-- MedPeer Initial Database Schema
-- This migration creates all the necessary tables for the MedPeer application

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create ENUM types
CREATE TYPE user_role AS ENUM ('student', 'doctor', 'nurse', 'pharmacist', 'lab_scientist', 'allied_health', 'admin');
CREATE TYPE post_type AS ENUM ('note', 'question', 'announcement', 'resource');
CREATE TYPE privacy_level AS ENUM ('public', 'followers', 'private');

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    first_name VARCHAR(64) NOT NULL,
    last_name VARCHAR(64) NOT NULL,
    role user_role NOT NULL DEFAULT 'student',
    institution VARCHAR(200),
    year_level VARCHAR(50),
    specialty VARCHAR(100),
    bio TEXT,
    profile_picture VARCHAR(200),
    location VARCHAR(100),
    website VARCHAR(200),
    linkedin VARCHAR(200),
    privacy_level privacy_level DEFAULT 'public',
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for users table
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_role ON users(role);

-- Posts table
CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    post_type post_type NOT NULL DEFAULT 'note',
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    is_flagged BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for posts table
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);
CREATE INDEX idx_posts_post_type ON posts(post_type);
CREATE INDEX idx_posts_is_deleted ON posts(is_deleted);
CREATE INDEX idx_posts_is_flagged ON posts(is_flagged);

-- Comments table
CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_flagged BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for comments table
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_created_at ON comments(created_at);
CREATE INDEX idx_comments_is_deleted ON comments(is_deleted);

-- Files table
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_hash VARCHAR(64),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    message_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    downloads INTEGER DEFAULT 0,
    is_scanned BOOLEAN DEFAULT FALSE,
    scan_result VARCHAR(50),
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for files table
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_post_id ON files(post_id);
CREATE INDEX idx_files_message_id ON files(message_id);
CREATE INDEX idx_files_created_at ON files(created_at);
CREATE INDEX idx_files_file_hash ON files(file_hash);

-- Messages table
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipient_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for messages table
CREATE INDEX idx_messages_sender_id ON messages(sender_id);
CREATE INDEX idx_messages_recipient_id ON messages(recipient_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_is_read ON messages(is_read);
CREATE INDEX idx_messages_conversation ON messages(sender_id, recipient_id, created_at);

-- Update foreign key constraint for files table
ALTER TABLE files ADD CONSTRAINT fk_files_message_id FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE;

-- Notifications table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    message VARCHAR(500) NOT NULL,
    notification_type VARCHAR(50) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    related_post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    related_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for notifications table
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_type ON notifications(notification_type);

-- Tags table
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(200),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for tags table
CREATE INDEX idx_tags_name ON tags(name);

-- Admin actions table
CREATE TABLE admin_actions (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL,
    description VARCHAR(500),
    admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    target_post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for admin_actions table
CREATE INDEX idx_admin_actions_admin_id ON admin_actions(admin_id);
CREATE INDEX idx_admin_actions_target_user_id ON admin_actions(target_user_id);
CREATE INDEX idx_admin_actions_created_at ON admin_actions(created_at);
CREATE INDEX idx_admin_actions_action_type ON admin_actions(action_type);

-- Content flags table
CREATE TABLE content_flags (
    id SERIAL PRIMARY KEY,
    reason VARCHAR(100) NOT NULL,
    description TEXT,
    reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    comment_id INTEGER REFERENCES comments(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for content_flags table
CREATE INDEX idx_content_flags_reporter_id ON content_flags(reporter_id);
CREATE INDEX idx_content_flags_post_id ON content_flags(post_id);
CREATE INDEX idx_content_flags_status ON content_flags(status);
CREATE INDEX idx_content_flags_created_at ON content_flags(created_at);

-- Site settings table
CREATE TABLE site_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description VARCHAR(200),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for site_settings table
CREATE INDEX idx_site_settings_key ON site_settings(key);

-- Association table for user followers
CREATE TABLE followers (
    follower_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    followed_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, followed_id),
    CHECK (follower_id != followed_id)
);

-- Create indexes for followers table
CREATE INDEX idx_followers_follower_id ON followers(follower_id);
CREATE INDEX idx_followers_followed_id ON followers(followed_id);

-- Association table for post tags
CREATE TABLE post_tags (
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (post_id, tag_id)
);

-- Create indexes for post_tags table
CREATE INDEX idx_post_tags_post_id ON post_tags(post_id);
CREATE INDEX idx_post_tags_tag_id ON post_tags(tag_id);

-- Create triggers for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers to relevant tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_posts_updated_at BEFORE UPDATE ON posts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_site_settings_updated_at BEFORE UPDATE ON site_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create full-text search indexes for better search performance
CREATE INDEX idx_posts_title_search ON posts USING gin(to_tsvector('english', title));
CREATE INDEX idx_posts_content_search ON posts USING gin(to_tsvector('english', content));
CREATE INDEX idx_users_name_search ON users USING gin(to_tsvector('english', first_name || ' ' || last_name));
CREATE INDEX idx_files_filename_search ON files USING gin(to_tsvector('english', original_filename));

-- Insert default site settings
INSERT INTO site_settings (key, value, description) VALUES
    ('site_name', 'MedPeer', 'Name of the website'),
    ('max_file_size', '52428800', 'Maximum file size in bytes (50MB)'),
    ('allowed_file_types', 'pdf,doc,docx,ppt,pptx,png,jpg,jpeg,mp4', 'Comma-separated list of allowed file extensions'),
    ('posts_per_page', '10', 'Number of posts to display per page'),
    ('enable_email_notifications', 'true', 'Enable email notifications'),
    ('maintenance_mode', 'false', 'Put site in maintenance mode');

-- Create database functions for common operations
CREATE OR REPLACE FUNCTION get_user_feed_posts(user_id_param INTEGER, limit_param INTEGER DEFAULT 20)
RETURNS TABLE (
    post_id INTEGER,
    post_title VARCHAR(200),
    post_content TEXT,
    post_type post_type,
    author_id INTEGER,
    author_name VARCHAR(129),
    author_username VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE,
    likes INTEGER,
    comment_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.title,
        p.content,
        p.post_type,
        u.id,
        u.first_name || ' ' || u.last_name,
        u.username,
        p.created_at,
        p.likes,
        COUNT(c.id) as comment_count
    FROM posts p
    JOIN users u ON p.user_id = u.id
    LEFT JOIN comments c ON p.id = c.post_id AND c.is_deleted = FALSE
    WHERE p.is_deleted = FALSE 
        AND (p.user_id = user_id_param 
             OR p.user_id IN (
                 SELECT followed_id 
                 FROM followers 
                 WHERE follower_id = user_id_param
             ))
    GROUP BY p.id, u.id, u.first_name, u.last_name, u.username
    ORDER BY p.created_at DESC
    LIMIT limit_param;
END;
$$ LANGUAGE plpgsql;

-- Create function to search content
CREATE OR REPLACE FUNCTION search_content(search_query TEXT, content_type VARCHAR DEFAULT 'all')
RETURNS TABLE (
    result_type VARCHAR(10),
    result_id INTEGER,
    title VARCHAR(200),
    content TEXT,
    author_name VARCHAR(129),
    created_at TIMESTAMP WITH TIME ZONE,
    relevance REAL
) AS $$
BEGIN
    IF content_type = 'all' OR content_type = 'posts' THEN
        RETURN QUERY
        SELECT 
            'post'::VARCHAR(10),
            p.id,
            p.title,
            LEFT(p.content, 200),
            u.first_name || ' ' || u.last_name,
            p.created_at,
            ts_rank(to_tsvector('english', p.title || ' ' || p.content), plainto_tsquery('english', search_query)) as relevance
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.is_deleted = FALSE
            AND (to_tsvector('english', p.title || ' ' || p.content) @@ plainto_tsquery('english', search_query))
        ORDER BY relevance DESC;
    END IF;
    
    IF content_type = 'all' OR content_type = 'users' THEN
        RETURN QUERY
        SELECT 
            'user'::VARCHAR(10),
            u.id,
            u.first_name || ' ' || u.last_name,
            COALESCE(u.bio, u.specialty, ''),
            u.first_name || ' ' || u.last_name,
            u.created_at,
            ts_rank(to_tsvector('english', u.first_name || ' ' || u.last_name || ' ' || u.username), plainto_tsquery('english', search_query)) as relevance
        FROM users u
        WHERE u.is_active = TRUE
            AND (to_tsvector('english', u.first_name || ' ' || u.last_name || ' ' || u.username) @@ plainto_tsquery('english', search_query))
        ORDER BY relevance DESC;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Comments for database documentation
COMMENT ON TABLE users IS 'Stores user account information and profiles';
COMMENT ON TABLE posts IS 'Main content posts created by users';
COMMENT ON TABLE comments IS 'Comments on posts';
COMMENT ON TABLE files IS 'File attachments for posts and messages';
COMMENT ON TABLE messages IS 'Direct messages between users';
COMMENT ON TABLE notifications IS 'System notifications for users';
COMMENT ON TABLE tags IS 'Tags that can be applied to posts';
COMMENT ON TABLE admin_actions IS 'Log of administrative actions taken';
COMMENT ON TABLE content_flags IS 'User reports of inappropriate content';
COMMENT ON TABLE site_settings IS 'Global application settings';
COMMENT ON TABLE followers IS 'User following relationships';
COMMENT ON TABLE post_tags IS 'Many-to-many relationship between posts and tags';

-- Grant permissions (adjust as needed for your deployment)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO medpeer_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO medpeer_app;
