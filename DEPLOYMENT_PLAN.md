# MVP Deployment Implementation Plan

## Executive Summary

This document outlines the deployment plan for the Financial Planning MVP, including database, backend (FastAPI), and frontend components. The plan covers multiple hosting options with cost considerations, focusing on Digital Ocean (your preference) while also presenting more affordable alternatives.

## Current Architecture Overview

### Backend
- **Framework**: FastAPI (Python)
- **Database**: Currently SQLite (needs migration to PostgreSQL for production)
- **Authentication**: JWT-based with access/refresh tokens
- **Key Dependencies**: 
  - TensorFlow 2.16.2 (heavy ML dependency)
  - SQLAlchemy 2.0.39
  - OpenAI API integration
  - Llama Cloud Services integration
- **File Storage**: Local file uploads (needs cloud storage for production)
- **Port**: 5000 (configurable)

### Frontend
- **Location**: Separate repository
- **Framework**: React/Vite (based on CORS configuration)
- **Port**: 3000 or 5173 (development)

### Database
- **Current**: SQLite (`app.db`)
- **Production**: PostgreSQL required

## Required Environment Variables

The following environment variables need to be configured:

```bash
# Authentication
SECRET_KEY=<strong-random-secret-key>
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database
DATABASE_URL=postgresql://user:password@host:port/dbname

# API Keys
OPENAI_API_KEY=<your-openai-api-key>
LLAMA_CLOUD_API_KEY=<your-llama-cloud-api-key>  # If required by llama-cloud-services

# CORS (for production)
FRONTEND_URL=https://your-frontend-domain.com
```

## Deployment Options Comparison

### Option 1: Digital Ocean (Your Preference)

**Pros:**
- You're familiar with the platform
- Good documentation and community support
- Flexible droplet sizes
- Managed PostgreSQL available
- Spaces for file storage

**Cons:**
- More expensive than some alternatives
- Requires more manual setup

**Estimated Monthly Cost:**
- App Droplet (2GB RAM, 1 vCPU): ~$12/month
- Managed PostgreSQL (1GB RAM): ~$15/month
- Spaces (250GB): ~$5/month
- **Total: ~$32/month**

**Setup Complexity:** Medium

---

### Option 2: Railway (Recommended for MVP - Most Affordable)

**Pros:**
- Very affordable ($5/month starter plan)
- Automatic deployments from GitHub
- Built-in PostgreSQL database
- Simple configuration
- Free tier available for testing
- Handles Docker or direct Python deployment

**Cons:**
- Less control than VPS
- Resource limits on free tier

**Estimated Monthly Cost:**
- Starter Plan: $5/month (includes $5 credit)
- PostgreSQL: Included in plan
- **Total: ~$5-10/month**

**Setup Complexity:** Low

---

### Option 3: Render

**Pros:**
- Affordable ($7/month for web services)
- Free PostgreSQL database
- Automatic SSL certificates
- Easy GitHub integration
- Good for Python/FastAPI

**Cons:**
- Services spin down after inactivity (free tier)
- Limited customization

**Estimated Monthly Cost:**
- Web Service: $7/month
- PostgreSQL: Free (or $7/month for production)
- **Total: ~$7-14/month**

**Setup Complexity:** Low

---

### Option 4: Fly.io

**Pros:**
- Very affordable (pay-as-you-go)
- Global edge deployment
- Good Docker support
- Free tier available

**Cons:**
- Requires Docker setup
- More complex than Railway/Render
- PostgreSQL requires separate service

**Estimated Monthly Cost:**
- App hosting: ~$2-5/month (based on usage)
- PostgreSQL (Supabase or Neon): Free tier available
- **Total: ~$2-10/month**

**Setup Complexity:** Medium-High

---

### Option 5: AWS/GCP/Azure

**Pros:**
- Highly scalable
- Enterprise-grade infrastructure
- Many managed services

**Cons:**
- Complex setup
- Can be expensive if not optimized
- Steeper learning curve
- Overkill for MVP

**Estimated Monthly Cost:** $20-50+/month

**Setup Complexity:** High

---

## Recommended Approach: Railway (Most Cost-Effective for MVP)

Given your focus on affordability and MVP deployment, **Railway** is recommended as the primary option. However, since you're familiar with Digital Ocean, both options are detailed below.

## Detailed Implementation Plan

### Phase 1: Pre-Deployment Preparation

#### 1.1 Database Migration (SQLite → PostgreSQL)
- [ ] Install PostgreSQL adapter: `psycopg2-binary` in requirements.txt
- [ ] Update `infra/database/base.py` to use PostgreSQL connection string
- [ ] Create database migration script to transfer data from SQLite to PostgreSQL
- [ ] Test migration locally with PostgreSQL

#### 1.2 Environment Configuration
- [ ] Create `.env.example` file with all required variables (no secrets)
- [ ] Document all environment variables in README
- [ ] Generate secure `SECRET_KEY` for production
- [ ] Obtain and document API keys (OpenAI, Llama Cloud)

#### 1.3 Code Updates for Production
- [ ] Update CORS settings in `api/main.py` to use environment variable for frontend URL
- [ ] Update database URL to read from environment variable
- [ ] Configure file upload storage (local for MVP, or cloud storage)
- [ ] Add health check endpoint (`/health`)
- [ ] Configure logging for production

#### 1.4 Docker Setup (Optional but Recommended)
- [ ] Create `Dockerfile` for backend
- [ ] Create `.dockerignore` file
- [ ] Test Docker build locally
- [ ] Create `docker-compose.yml` for local development with PostgreSQL

#### 1.5 Frontend Configuration
- [ ] Update frontend API base URL to production endpoint
- [ ] Configure CORS on backend to allow frontend domain
- [ ] Build frontend for production
- [ ] Test frontend-backend integration

---

### Phase 2: Railway Deployment (Recommended)

#### 2.1 Railway Account Setup
- [ ] Create Railway account (railway.app)
- [ ] Connect GitHub repository
- [ ] Create new project

#### 2.2 Database Setup
- [ ] Add PostgreSQL service to Railway project
- [ ] Copy database connection string
- [ ] Run database migrations (create tables)
- [ ] Verify database connection

#### 2.3 Backend Deployment
- [ ] Create new service from GitHub repo
- [ ] Configure build command: `pip install -r requirements.txt`
- [ ] Configure start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- [ ] Set environment variables:
  - `DATABASE_URL` (from PostgreSQL service)
  - `SECRET_KEY`
  - `OPENAI_API_KEY`
  - `LLAMA_CLOUD_API_KEY` (if needed)
  - `FRONTEND_URL`
  - Other auth variables
- [ ] Deploy and verify health endpoint

#### 2.4 Frontend Deployment
- [ ] Create new service for frontend (or use separate Railway project)
- [ ] Configure build command (e.g., `npm run build` or `yarn build`)
- [ ] Configure start command for static hosting
- [ ] Set environment variables (API URL, etc.)
- [ ] Deploy and test

#### 2.5 Post-Deployment
- [ ] Test all API endpoints
- [ ] Verify authentication flow
- [ ] Test file uploads
- [ ] Verify database operations
- [ ] Set up custom domain (optional)
- [ ] Configure SSL (automatic with Railway)

---

### Phase 3: Digital Ocean Deployment (Alternative)

#### 3.1 Infrastructure Setup
- [ ] Create Droplet (Ubuntu 22.04, 2GB RAM minimum)
- [ ] Set up firewall (allow ports 22, 80, 443, 5000)
- [ ] Create managed PostgreSQL database
- [ ] Create Spaces bucket for file storage (optional)

#### 3.2 Server Configuration
- [ ] SSH into droplet
- [ ] Update system packages
- [ ] Install Python 3.11+
- [ ] Install PostgreSQL client
- [ ] Create application user
- [ ] Set up application directory

#### 3.3 Application Deployment
- [ ] Clone repository
- [ ] Create virtual environment
- [ ] Install dependencies
- [ ] Create `.env` file with all variables
- [ ] Run database migrations
- [ ] Test application locally on server

#### 3.4 Process Management
- [ ] Install and configure systemd service for backend
- [ ] Configure service to auto-start on boot
- [ ] Set up log rotation
- [ ] Configure reverse proxy (Nginx)

#### 3.5 Nginx Configuration
- [ ] Install Nginx
- [ ] Configure Nginx as reverse proxy for backend
- [ ] Configure static file serving for frontend (or separate frontend deployment)
- [ ] Set up SSL with Let's Encrypt
- [ ] Configure domain DNS

#### 3.6 Frontend Deployment
- [ ] Option A: Build and serve from Nginx
- [ ] Option B: Deploy to separate service (e.g., Netlify, Vercel)
- [ ] Update API URLs in frontend
- [ ] Test end-to-end

---

### Phase 4: Database Migration

#### 4.1 Migration Strategy
- [ ] Export data from SQLite (if needed)
- [ ] Create PostgreSQL database schema
- [ ] Run SQLAlchemy migrations or create tables
- [ ] Import data (if migrating existing data)
- [ ] Verify data integrity

#### 4.2 Migration Script
Create a script to:
- Connect to both databases
- Transfer schema
- Transfer data (if applicable)
- Verify counts and integrity

---

### Phase 5: File Storage

#### 5.1 Current State
- Files stored in `uploads/` directory locally

#### 5.2 Production Options
- **Option A**: Keep local storage (simplest for MVP)
  - Ensure directory exists and has write permissions
  - Set up backup strategy
  
- **Option B**: Cloud storage (recommended for scale)
  - Digital Ocean Spaces
  - AWS S3
  - Cloudinary
  - Update upload service to use cloud storage

---

### Phase 6: Monitoring & Maintenance

#### 6.1 Basic Monitoring
- [ ] Set up application logging
- [ ] Configure error tracking (Sentry, optional)
- [ ] Set up uptime monitoring (UptimeRobot, free tier)
- [ ] Configure email alerts for critical errors

#### 6.2 Backup Strategy
- [ ] Automated database backups (daily)
- [ ] Backup retention policy (7-30 days)
- [ ] Test restore procedure
- [ ] Document backup/restore process

#### 6.3 Security
- [ ] Review and harden security settings
- [ ] Ensure all secrets are in environment variables
- [ ] Configure rate limiting (optional)
- [ ] Set up firewall rules
- [ ] Regular security updates

---

## Step-by-Step Checklist

### Immediate Actions (Before Deployment)

- [ ] **Review and update `requirements.txt`**
  - Add `psycopg2-binary` for PostgreSQL
  - Verify all dependencies are production-ready

- [ ] **Create environment configuration**
  - Create `.env.example` template
  - Document all required variables

- [ ] **Update database configuration**
  - Modify `infra/database/base.py` to read `DATABASE_URL` from environment
  - Remove SQLite-specific connection args

- [ ] **Update CORS settings**
  - Change hardcoded localhost URLs to environment variable
  - Allow production frontend domain

- [ ] **Create database migration script**
  - Script to create all tables in PostgreSQL
  - Optional: Data migration from SQLite

- [ ] **Add health check endpoint**
  - Simple `/health` endpoint for monitoring

- [ ] **Test locally with PostgreSQL**
  - Install PostgreSQL locally
  - Test database connection
  - Verify all functionality

### Deployment Actions

#### For Railway:
- [ ] Sign up for Railway
- [ ] Connect GitHub repo
- [ ] Create PostgreSQL service
- [ ] Create backend service
- [ ] Configure environment variables
- [ ] Deploy and test
- [ ] Deploy frontend (separate service or external)

#### For Digital Ocean:
- [ ] Create Droplet
- [ ] Set up server (Python, PostgreSQL client)
- [ ] Create managed PostgreSQL database
- [ ] Clone and configure application
- [ ] Set up systemd service
- [ ] Configure Nginx
- [ ] Set up SSL
- [ ] Deploy frontend

### Post-Deployment Actions

- [ ] Test all API endpoints
- [ ] Verify authentication
- [ ] Test file uploads
- [ ] Verify database operations
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Document deployment process
- [ ] Create runbook for common issues

---

## Cost Comparison Summary

| Provider | Monthly Cost | Setup Time | Best For |
|----------|-------------|------------|----------|
| **Railway** | $5-10 | 1-2 hours | MVP, quick deployment |
| **Render** | $7-14 | 1-2 hours | Python apps, simplicity |
| **Fly.io** | $2-10 | 2-4 hours | Docker apps, global edge |
| **Digital Ocean** | $32+ | 4-6 hours | Full control, familiarity |
| **AWS/GCP** | $20-50+ | 6+ hours | Enterprise, scale |

---

## Recommendations

1. **For MVP**: Start with **Railway** - fastest, cheapest, easiest
2. **If you prefer Digital Ocean**: Use it - you're familiar, and it's reliable
3. **Frontend**: Consider deploying frontend separately to **Netlify** or **Vercel** (free tier available)
4. **Database**: Use managed PostgreSQL (Railway, Digital Ocean, or Supabase)
5. **File Storage**: Start with local storage, migrate to cloud storage later if needed

---

## Next Steps

1. Choose deployment platform (Railway recommended for cost)
2. Complete Phase 1 preparation tasks
3. Set up database (PostgreSQL)
4. Deploy backend
5. Deploy frontend
6. Test thoroughly
7. Set up monitoring and backups

---

## Notes

- TensorFlow is a large dependency (~500MB+). Consider:
  - Using a Docker image with TensorFlow pre-installed
  - Or ensure sufficient build time/resources on hosting platform
  
- File uploads: For MVP, local storage is fine. Consider cloud storage (S3, Spaces) if:
  - Files exceed server storage
  - Need redundancy
  - Multiple server instances

- Frontend deployment: If frontend is in separate repo, deploy separately. Options:
  - Netlify (free tier)
  - Vercel (free tier)
  - Railway (same project, separate service)
  - Digital Ocean (same server or separate)

---

## Questions to Resolve

1. Do you have the frontend repository ready for deployment?
2. What is your expected traffic/user load for MVP?
3. Do you need to migrate existing SQLite data, or start fresh?
4. What is your preferred domain name?
5. Do you have API keys for OpenAI and Llama Cloud Services ready?

---

## Additional Resources

- Railway Docs: https://docs.railway.app
- Digital Ocean App Platform: https://docs.digitalocean.com/products/app-platform/
- FastAPI Deployment: https://fastapi.tiangolo.com/deployment/
- PostgreSQL Migration: https://www.postgresql.org/docs/current/migration.html

