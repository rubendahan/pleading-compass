
CREATE SCHEMA IF NOT EXISTS private;
GRANT USAGE ON SCHEMA private TO authenticated, service_role;

-- Recreate helpers inside `private` (still SECURITY DEFINER — needed so they can read user_roles/profiles bypassing RLS recursion).
CREATE OR REPLACE FUNCTION private.has_role(_user_id uuid, _role public.app_role)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role);
$$;

CREATE OR REPLACE FUNCTION private.current_firm_id()
RETURNS uuid LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT firm_id FROM public.profiles WHERE id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION private.is_firm_admin(_firm_id uuid)
RETURNS boolean LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.user_roles
    WHERE user_id = auth.uid() AND role = 'firm_admin' AND firm_id = _firm_id
  );
$$;

REVOKE ALL ON FUNCTION private.has_role(uuid, public.app_role) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION private.current_firm_id() FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION private.is_firm_admin(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION private.has_role(uuid, public.app_role) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.current_firm_id() TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION private.is_firm_admin(uuid) TO authenticated, service_role;

-- Recreate all policies to reference the private helpers.
DROP POLICY IF EXISTS "firm admins delete cases" ON public.cases;
DROP POLICY IF EXISTS "firm members insert cases" ON public.cases;
DROP POLICY IF EXISTS "firm members read cases" ON public.cases;
DROP POLICY IF EXISTS "firm members update cases" ON public.cases;
DROP POLICY IF EXISTS "admins update their firm" ON public.firms;
DROP POLICY IF EXISTS "members read their firm" ON public.firms;
DROP POLICY IF EXISTS "user reads firm-mates" ON public.profiles;
DROP POLICY IF EXISTS "admin reads firm roles" ON public.user_roles;

CREATE POLICY "firm admins delete cases" ON public.cases FOR DELETE TO authenticated
  USING (private.is_firm_admin(firm_id));
CREATE POLICY "firm members insert cases" ON public.cases FOR INSERT TO authenticated
  WITH CHECK (firm_id = private.current_firm_id());
CREATE POLICY "firm members read cases" ON public.cases FOR SELECT TO authenticated
  USING (firm_id = private.current_firm_id());
CREATE POLICY "firm members update cases" ON public.cases FOR UPDATE TO authenticated
  USING (firm_id = private.current_firm_id());

CREATE POLICY "admins update their firm" ON public.firms FOR UPDATE TO authenticated
  USING (private.is_firm_admin(id));
CREATE POLICY "members read their firm" ON public.firms FOR SELECT TO authenticated
  USING (id = private.current_firm_id());

CREATE POLICY "user reads firm-mates" ON public.profiles FOR SELECT TO authenticated
  USING (firm_id IS NOT NULL AND firm_id = private.current_firm_id());

CREATE POLICY "admin reads firm roles" ON public.user_roles FOR SELECT TO authenticated
  USING (firm_id IS NOT NULL AND private.is_firm_admin(firm_id));

-- Drop the now-unused public copies so they aren't exposed via PostgREST.
DROP FUNCTION IF EXISTS public.has_role(uuid, public.app_role);
DROP FUNCTION IF EXISTS public.current_firm_id();
DROP FUNCTION IF EXISTS public.is_firm_admin(uuid);
