-- Migration: Add status column to interventions table
-- Description: Add status tracking (Pending, In Progress, Completed) instead of deleting interventions

USE it_asset_management;

-- Add status column to interventions if it doesn't exist
ALTER TABLE interventions ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Pending' AFTER intervention_date;

-- Add created_at and updated_at for better tracking
ALTER TABLE interventions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP AFTER status;
ALTER TABLE interventions ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

-- Add index for status to improve query performance
CREATE INDEX IF NOT EXISTS idx_interventions_status ON interventions(status);
CREATE INDEX IF NOT EXISTS idx_interventions_asset_id ON interventions(asset_id);
