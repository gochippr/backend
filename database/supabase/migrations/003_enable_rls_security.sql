-- Migration: Enable RLS for users and user_plaid_items tables
-- This migration implements Row Level Security policies for multi-tenant data isolation
-- Compatible with Supabase's security model and handles existing policies

-- Step 1: Enable RLS on both tables (if not already enabled)
-- Check if RLS is already enabled before attempting to enable
DO $$ 
BEGIN
    -- Enable RLS on users table if not already enabled
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename = 'users' 
        AND rowsecurity = true
    ) THEN
        ALTER TABLE users ENABLE ROW LEVEL SECURITY;
    END IF;

    -- Enable RLS on user_plaid_items table if not already enabled
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename = 'user_plaid_items' 
        AND rowsecurity = true
    ) THEN
        ALTER TABLE user_plaid_items ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

-- Step 2: Drop existing policies if they exist (to ensure clean state)
-- This is safe as we'll recreate them immediately
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Enable insert for authentication" ON users;
DROP POLICY IF EXISTS "Users can delete own profile" ON users;
DROP POLICY IF EXISTS "Admin can view all users" ON users;

DROP POLICY IF EXISTS "Users can view own plaid items" ON user_plaid_items;
DROP POLICY IF EXISTS "Users can insert own plaid items" ON user_plaid_items;
DROP POLICY IF EXISTS "Users can update own plaid items" ON user_plaid_items;
DROP POLICY IF EXISTS "Users can delete own plaid items" ON user_plaid_items;
DROP POLICY IF EXISTS "Admin can view all plaid items" ON user_plaid_items;

-- Step 3: Create Users table policies

-- Policy: Users can only view their own profile
CREATE POLICY "Users can view own profile" 
ON users FOR SELECT 
USING (id = auth.uid()::text);

-- Policy: Users can update their own profile
CREATE POLICY "Users can update own profile" 
ON users FOR UPDATE 
USING (id = auth.uid()::text)
WITH CHECK (id = auth.uid()::text);

-- Policy: Allow user creation during signup
CREATE POLICY "Enable insert for authentication" 
ON users FOR INSERT 
WITH CHECK (id = auth.uid()::text);

-- Step 4: Create User Plaid Items table policies

-- Policy: Users can only view their own Plaid items
CREATE POLICY "Users can view own plaid items" 
ON user_plaid_items FOR SELECT 
USING (user_id = auth.uid()::text);

-- Policy: Users can insert their own Plaid items
CREATE POLICY "Users can insert own plaid items" 
ON user_plaid_items FOR INSERT 
WITH CHECK (user_id = auth.uid()::text);

-- Policy: Users can update their own Plaid items
CREATE POLICY "Users can update own plaid items" 
ON user_plaid_items FOR UPDATE 
USING (user_id = auth.uid()::text)
WITH CHECK (user_id = auth.uid()::text);

-- Policy: Users can delete their own Plaid items
CREATE POLICY "Users can delete own plaid items" 
ON user_plaid_items FOR DELETE 
USING (user_id = auth.uid()::text);

-- Step 5: Create or replace trigger functions

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS ensure_user_id_matches_auth ON user_plaid_items;
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
DROP TRIGGER IF EXISTS update_user_plaid_items_updated_at ON user_plaid_items;

-- Create a function to validate user_id on insert for plaid items
CREATE OR REPLACE FUNCTION public.handle_user_plaid_items_insert()
RETURNS TRIGGER AS $$
BEGIN
  -- Ensure user_id matches the authenticated user
  IF NEW.user_id != auth.uid()::text THEN
    RAISE EXCEPTION 'user_id must match authenticated user';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to validate user_id
CREATE TRIGGER ensure_user_id_matches_auth
  BEFORE INSERT ON user_plaid_items
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_user_plaid_items_insert();

-- Create or replace updated_at trigger function
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create updated_at triggers
CREATE TRIGGER update_users_updated_at 
  BEFORE UPDATE ON users 
  FOR EACH ROW 
  EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER update_user_plaid_items_updated_at 
  BEFORE UPDATE ON user_plaid_items 
  FOR EACH ROW 
  EXECUTE FUNCTION public.handle_updated_at();

-- Step 6: Create or replace helper view for easier querying
DROP VIEW IF EXISTS my_plaid_items;
CREATE VIEW my_plaid_items AS
SELECT * FROM user_plaid_items
WHERE user_id = auth.uid()::text;

-- Grant access to the view
GRANT SELECT ON my_plaid_items TO authenticated;

-- Step 7: Create performance indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_user_plaid_items_user_id ON user_plaid_items(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plaid_items_active ON user_plaid_items(is_active) WHERE is_active = true;

-- Step 8: Verify the migration succeeded
DO $$ 
DECLARE
    policy_count INTEGER;
BEGIN
    -- Count policies on users table
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies 
    WHERE schemaname = 'public' AND tablename = 'users';
    
    IF policy_count < 3 THEN
        RAISE WARNING 'Expected at least 3 policies on users table, found %', policy_count;
    END IF;
    
    -- Count policies on user_plaid_items table
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies 
    WHERE schemaname = 'public' AND tablename = 'user_plaid_items';
    
    IF policy_count < 4 THEN
        RAISE WARNING 'Expected at least 4 policies on user_plaid_items table, found %', policy_count;
    END IF;
    
    RAISE NOTICE 'RLS migration completed successfully';
END $$;

-- Optional: List all created policies for verification
/*
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd
FROM pg_policies 
WHERE tablename IN ('users', 'user_plaid_items')
ORDER BY tablename, policyname;
*/