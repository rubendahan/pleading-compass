
-- Enums
CREATE TYPE public.app_role AS ENUM ('firm_admin', 'lawyer');

-- Firms
CREATE TABLE public.firms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.firms TO authenticated;
GRANT ALL ON public.firms TO service_role;
ALTER TABLE public.firms ENABLE ROW LEVEL SECURITY;

-- Profiles (1:1 with auth.users)
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  firm_id UUID REFERENCES public.firms(id) ON DELETE SET NULL,
  full_name TEXT,
  email TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.profiles TO authenticated;
GRANT ALL ON public.profiles TO service_role;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Roles
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role public.app_role NOT NULL,
  firm_id UUID REFERENCES public.firms(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (user_id, role, firm_id)
);
GRANT SELECT ON public.user_roles TO authenticated;
GRANT ALL ON public.user_roles TO service_role;
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

-- Cases
CREATE TABLE public.cases (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  firm_id UUID NOT NULL REFERENCES public.firms(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  claim_no TEXT,
  court TEXT,
  data JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.cases TO authenticated;
GRANT ALL ON public.cases TO service_role;
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;

-- Security definer helpers (avoid RLS recursion)
CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role public.app_role)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role);
$$;

CREATE OR REPLACE FUNCTION public.current_firm_id()
RETURNS UUID LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT firm_id FROM public.profiles WHERE id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION public.is_firm_admin(_firm_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = auth.uid() AND role = 'firm_admin' AND firm_id = _firm_id
  );
$$;

-- Policies: firms
CREATE POLICY "members read their firm" ON public.firms FOR SELECT
  TO authenticated USING (id = public.current_firm_id());
CREATE POLICY "admins update their firm" ON public.firms FOR UPDATE
  TO authenticated USING (public.is_firm_admin(id));

-- Policies: profiles
CREATE POLICY "user reads own profile" ON public.profiles FOR SELECT
  TO authenticated USING (id = auth.uid());
CREATE POLICY "user reads firm-mates" ON public.profiles FOR SELECT
  TO authenticated USING (firm_id IS NOT NULL AND firm_id = public.current_firm_id());
CREATE POLICY "user updates own profile" ON public.profiles FOR UPDATE
  TO authenticated USING (id = auth.uid());
CREATE POLICY "user inserts own profile" ON public.profiles FOR INSERT
  TO authenticated WITH CHECK (id = auth.uid());

-- Policies: user_roles
CREATE POLICY "user reads own roles" ON public.user_roles FOR SELECT
  TO authenticated USING (user_id = auth.uid());
CREATE POLICY "admin reads firm roles" ON public.user_roles FOR SELECT
  TO authenticated USING (firm_id IS NOT NULL AND public.is_firm_admin(firm_id));

-- Policies: cases (firm-wide read; lawyers can write; admins can delete)
CREATE POLICY "firm members read cases" ON public.cases FOR SELECT
  TO authenticated USING (firm_id = public.current_firm_id());
CREATE POLICY "firm members insert cases" ON public.cases FOR INSERT
  TO authenticated WITH CHECK (firm_id = public.current_firm_id());
CREATE POLICY "firm members update cases" ON public.cases FOR UPDATE
  TO authenticated USING (firm_id = public.current_firm_id());
CREATE POLICY "firm admins delete cases" ON public.cases FOR DELETE
  TO authenticated USING (public.is_firm_admin(firm_id));

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;
CREATE TRIGGER cases_set_updated BEFORE UPDATE ON public.cases
  FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Auto-create profile row on signup (firm assignment happens via server fn after signup)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name)
  VALUES (NEW.id, NEW.email, NEW.raw_user_meta_data->>'full_name')
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END; $$;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
