-- Create transaction_categories table
CREATE TABLE IF NOT EXISTS transaction_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    color VARCHAR(7), -- Hex color code
    icon VARCHAR(50), -- Icon identifier
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default categories
INSERT INTO transaction_categories (name, description, color, icon) VALUES
    ('Food & Dining', 'Restaurants, groceries, and dining expenses', '#FF6B6B', 'utensils'),
    ('Transportation', 'Gas, public transit, rideshare, and vehicle expenses', '#4ECDC4', 'car'),
    ('Entertainment', 'Movies, concerts, events, and leisure activities', '#45B7D1', 'film'),
    ('Shopping', 'Clothing, electronics, and general retail', '#96CEB4', 'shopping-bag'),
    ('Healthcare', 'Medical expenses, prescriptions, and health services', '#FFEAA7', 'heartbeat'),
    ('Utilities', 'Electricity, water, gas, internet, and phone bills', '#DDA0DD', 'bolt'),
    ('Housing', 'Rent, mortgage, and home maintenance', '#98D8C8', 'home'),
    ('Travel', 'Vacations, flights, hotels, and travel expenses', '#F7DC6F', 'plane'),
    ('Education', 'Tuition, books, courses, and educational expenses', '#BB8FCE', 'graduation-cap'),
    ('Business', 'Work-related expenses and business costs', '#85C1E9', 'briefcase'),
    ('Other', 'Miscellaneous and uncategorized expenses', '#BDC3C7', 'ellipsis-h')
ON CONFLICT (name) DO NOTHING; 