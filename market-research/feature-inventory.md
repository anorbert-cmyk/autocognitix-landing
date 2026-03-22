# AutoCognitix - Complete Feature Inventory for Landing Page

**Repository:** https://github.com/anorbert-cmyk/AutoCognitix  
**Status:** Production-Ready (Sprint 7.5 Complete)  
**Last Updated:** 2026-03-20  
**Language Support:** English & Hungarian

---

## Executive Summary

AutoCognitix is an **AI-powered vehicle diagnostic platform** that combines Retrieval-Augmented Generation (RAG), semantic search, and comprehensive automotive databases to provide intelligent vehicle issue diagnosis. The platform requires no hardware and supports full Hungarian language processing.

### Core Value Proposition
- **AI-Driven Diagnosis:** Uses Claude/GPT-4 with RAG for intelligent problem analysis
- **Hardware-Free:** Manual DTC code and symptom input (no OBD-II scanner needed)
- **Hungarian-First:** Native Hungarian language support with huBERT embeddings
- **Knowledge Integration:** Combines OBD-II codes, TSB data, NHTSA recalls, and forum wisdom
- **Enterprise-Ready:** Production deployment on Railway with PostgreSQL, Neo4j, and Qdrant

---

## Section 1: Complete Feature Set

### 1.1 Core Diagnostic Features

#### AI-Powered Diagnosis Analysis
- **RAG Pipeline:** Retrieval-Augmented Generation using LangChain
- **Hybrid Retrieval:** Multi-source context from Qdrant (vector), Neo4j (graph), and PostgreSQL (text)
- **LLM Integration:** Supports Anthropic Claude, OpenAI GPT-4, and Ollama (fallback)
- **Streaming Output:** Real-time diagnosis via Server-Sent Events (SSE)
- **Confidence Scoring:** Confidence levels (high/medium/low) for each diagnosis
- **Multi-Language Output:** Automatic translation between Hungarian and English

**Key Capabilities:**
- Analyzes up to 10 DTC codes simultaneously
- Processes detailed symptom descriptions in Hungarian
- Calculates repair costs (parts + labor)
- Identifies probable causes with confidence scores
- Provides step-by-step diagnostic procedures
- Recommends specialized tools required
- Suggests root cause analysis

#### Request/Response Schema (POST `/api/v1/diagnosis/analyze`)
```
Input:
- DTC codes (e.g., "P0101, P0171")
- Symptom description (Hungarian text)
- Vehicle make/model/year
- Optional VIN, engine code, mileage

Output:
- Diagnosis ID (UUID)
- Probable causes (with confidence scores)
- Recommended repairs (with cost estimates)
- Related DTC codes
- Suggested diagnostic tools
- Confidence score (0-1)
- Processing sources
```

**Feature Details:**
- Estimated cost in HUF (Hungarian Forint)
- Difficulty levels: easy, intermediate, advanced, expert
- Estimated repair time in minutes
- Parts list with pricing
- Labor cost breakdown

#### Streaming Diagnosis Endpoint
- **Endpoint:** `POST /api/v1/diagnosis/analyze-stream`
- **Protocol:** Server-Sent Events (SSE)
- **Max Duration:** 5 minutes per stream
- **Concurrent Limit:** 10 concurrent streams
- **Response Format:** JSON event stream with diagnosis progress
- **Real-Time Updates:** Client sees analysis as it progresses

### 1.2 DTC Code Database

#### Database Capabilities
- **Total Codes:** 63+ standardized OBD-II DTC codes (P, B, C, U prefixes)
- **Languages:** English + Hungarian descriptions
- **Metadata Per Code:**
  - Code category (powertrain, body, chassis, network)
  - Severity level (low, medium, high, critical)
  - Generic vs. manufacturer-specific flags
  - System classification (fuel/air, emission, transmission, etc.)
  - Symptoms (array of possible user-facing issues)
  - Possible causes (technical root causes)
  - Diagnostic steps (repair procedure)
  - Related codes (cross-references)

#### DTC Search Features
- **Semantic Search:** Find similar issues using huBERT embeddings
- **Keyword Search:** Full-text search in code descriptions
- **Vector Search:** Qdrant-powered cosine similarity matching
- **Filtering:** By category, severity, generic/manufacturer status
- **Autocomplete:** DTC code suggestions as user types
- **Relevance Scoring:** Search results ranked by relevance

#### DTC Detail Endpoint
- **GET** `/api/v1/dtc/{code}` - Full code details
- **GET** `/api/v1/dtc/search` - Keyword/semantic search
- **GET** `/api/v1/dtc/{code}/related` - Related codes
- **Performance:** Redis cached (1-hour TTL)

### 1.3 Vehicle Information System

#### VIN Decoding
- **Source:** NHTSA vPIC API
- **Input:** 17-character VIN
- **Output:** Complete vehicle details
  - Make, model, year
  - Trim/body class
  - Engine specs (displacement, cylinders, fuel type)
  - Transmission type
  - Drive type (FWD, RWD, AWD)
  - Region/origin determination
  - Manufacturing country

**Validation:**
- VIN length validation (exactly 17 chars)
- Invalid character detection (I, O, Q not allowed)
- Check digit validation (Luhn algorithm)

#### Vehicle Database (Neo4j)
- **Total Vehicles:** 8,145+ make/model/year combinations
- **Makes:** 150+ manufacturers
- **Data Points Per Vehicle:**
  - Model years and production ranges
  - Body types (sedan, coupe, hatchback, wagon, SUV, truck)
  - Engine codes
  - Platform information
  - Common issues (DTC frequency)

#### Vehicle Hierarchy
1. Makes (manufacturers: VW, BMW, Toyota, etc.)
2. Models (Golf, 3 Series, Camry, etc.)
3. Years (2020-2026)
4. Engine variants
5. Common issues per combination

#### Vehicle Endpoints
- **GET** `/api/v1/vehicles/makes` - List manufacturers
- **GET** `/api/v1/vehicles/models` - Models for make
- **GET** `/api/v1/vehicles/years` - Available years
- **POST** `/api/v1/vehicles/decode-vin` - VIN decoding
- **GET** `/api/v1/vehicles/{make}/{model}/{year}/recalls` - Safety recalls
- **GET** `/api/v1/vehicles/{make}/{model}/{year}/complaints` - Consumer complaints
- **GET** `/api/v1/vehicles/{make}/{model}/common-issues` - Frequent issues

### 1.4 NHTSA Integration

#### Recalls Database
- **Source:** NHTSA Safety Recall API
- **Data Includes:**
  - Campaign number
  - Recall date
  - Component affected
  - Safety summary
  - Consequence description
  - Remedy procedure
  - Manufacturer info
  - NHTSA ID reference

#### Complaints Database
- **Source:** NHTSA Complaints API
- **Data Includes:**
  - Complaint date
  - Incident date
  - Component complained about
  - Summary text
  - Crash indicators
  - Fire indicators
  - Injury count
  - Death count
  - ODI number (tracking ID)

#### Safety Features
- Real-time recall lookup for any vehicle
- Consumer complaint analysis
- Safety trend identification
- Component failure tracking

### 1.5 Knowledge Graph (Neo4j)

#### Graph Structure
```
Vehicle → (HAS_COMMON) → DTC
DTC → (CAUSES) → Symptom
DTC → (AFFECTS) → Component
Component → (REQUIRES) → Repair
Repair → (NEEDS) → Part
DTC → (RELATED_TO) → DTC
```

#### Graph Capabilities
- **Path Finding:** Diagnostic path from symptom → DTC → cause → repair
- **Relationship Mapping:** Components linked to DTCs linked to symptoms
- **Common Issues:** Frequency analysis for vehicle make/model/year
- **Related Codes:** Find similar problems and solutions
- **Repair Workflows:** Multi-step repair procedures

#### Data Volume
- 26,816+ nodes (vehicles, DTCs, components, repairs)
- Relationship edges connecting all entities
- Community detection for issue clusters

### 1.6 Vector Search (Qdrant)

#### Embedding Technology
- **Model:** huBERT (SZTAKI-HLT/hubert-base-cc)
- **Dimensions:** 768-dimensional vectors
- **Language:** Hungarian-optimized BERT variant
- **Similarity Metric:** Cosine similarity

#### Use Cases
1. **Symptom Matching:** Find DTC codes matching symptom descriptions
2. **Issue Similarity:** Locate similar known issues
3. **Knowledge Retrieval:** Find relevant repair procedures
4. **Semantic Search:** Find issues even with different wording

#### Database Size
- 35,000+ indexed vectors
- Covers all DTC codes, symptoms, and known issues
- No API rate limits (local model)

### 1.7 Parts & Pricing Service

#### Functionality
- **Part-DTC Mapping:** Links which parts are needed for each DTC
- **Price Estimation:** Min/max price ranges for parts
- **Labor Cost Estimation:** By difficulty level (easy/medium/hard/expert)
- **Total Cost Calculation:** Parts + labor estimate

#### Pricing Data
**Fallback Static Prices (HUF):**
- Oxygen Sensor: 12,000-85,000 HUF
- Catalytic Converter: 80,000-450,000 HUF
- MAF Sensor: 15,000-85,000 HUF
- Air Filter: 3,000-15,000 HUF
- Spark Plugs: 1,500-8,000 HUF
- Ignition Coil: 8,000-45,000 HUF
- EGR Valve: 25,000-120,000 HUF

**Labor Rates (HUF/hour):**
- Easy: 8,000-15,000
- Medium: 12,000-25,000
- Hard: 20,000-40,000
- Expert: 35,000-60,000

#### Caching
- 24-hour Redis cache TTL
- Falls back to static data if external source unavailable

---

## Section 2: User Management & Authentication

### 2.1 Authentication System

#### Registration
- **Endpoint:** `POST /api/v1/auth/register`
- **Required Fields:** Email, password, full name
- **Password Requirements:**
  - Minimum length validation
  - Strength meter (visual feedback)
  - Bcrypt hashing with salt
- **Email Verification:** Optional email verification token
- **Response:** Access token, refresh token, user profile

#### Login
- **Endpoint:** `POST /api/v1/auth/login`
- **Method:** OAuth2 password flow
- **Response:** Access token (30 min), Refresh token (7 days)
- **Security:** Account lockout after failed attempts

#### Token Management
- **Access Token:** 30-minute expiration
- **Refresh Token:** 7-day expiration
- **Refresh Endpoint:** `POST /api/v1/auth/refresh`
- **Logout:** Invalidates tokens via blacklist
- **Cookie-based:** httpOnly, Secure, SameSite flags

#### Account Security
- **Account Lockout:** Automatic after N failed login attempts
- **Lockout Duration:** Configurable (default 15 minutes)
- **Failed Login Tracking:** Timestamp of last attempt
- **Login History:** Last login timestamp stored

#### Password Management
- **Reset Flow:** Forgot password → email token → reset with new password
- **Reset Endpoint:** `POST /api/v1/auth/forgot-password`
- **Token Expiry:** Reset tokens expire after 24 hours
- **Verification:** Email verification before reset completion

### 2.2 User Roles & Permissions

#### Role Hierarchy
1. **User** (default) - Regular users
2. **Mechanic** - Professional mechanics with extended features
3. **Admin** - System administrators

#### Permission Matrix
| Action | User | Mechanic | Admin |
|--------|------|----------|-------|
| Run diagnosis | ✓ | ✓ | ✓ |
| View history | ✓ | ✓ | ✓ |
| Share diagnosis | ✓ | ✓ | ✓ |
| Manage users | ✗ | ✗ | ✓ |
| View metrics | ✗ | ✓ | ✓ |
| Export reports | ✓ | ✓ | ✓ |

#### User Profile
- **Endpoint:** `GET/PUT /api/v1/auth/profile`
- **Editable Fields:** Full name, email, password
- **Read-Only:** User ID, role, created date, last login

---

## Section 3: Frontend User Interface

### 3.1 Pages & User Flows

#### Home Page (Public)
- **URL:** `/`
- **Features:**
  - Hero section with CTA buttons
  - Feature overview (3 main capabilities)
  - Demo button to show sample diagnosis
  - Call-to-action to start diagnosis
  - Responsive design (mobile-first)
- **Styling:** TailwindCSS with gradient backgrounds
- **Languages:** Hungarian primary, English fallback

#### Diagnosis Page (Private)
- **URL:** `/diagnosis` (redirects to new diagnosis)
- **Features:**
  - DTC code input field
  - Symptom description text area
  - Vehicle selector (make/model/year)
  - VIN optional input
  - Multi-language support (HU/EN)
- **Components:**
  - Wizard stepper (4 steps)
  - Form validation with visual feedback
  - Real-time DTC autocomplete
  - Symptom suggestions

#### New Diagnosis Page
- **URL:** `/new-diagnosis`
- **Features:**
  - Fresh diagnosis form
  - Clear form state
  - Saved vehicles quick-select
  - Example DTCs (P0101, P0420, P0171)

#### Result Page (Analysis Results)
- **URL:** `/results/{diagnosisId}`
- **Sections:**
  1. **Diagnosis Summary**
     - Vehicle info (make/model/year/VIN)
     - Input codes and symptoms
     - Overall confidence score
  
  2. **Probable Causes**
     - List with confidence levels
     - Description and severity
     - Related DTC codes
     - Component affected
  
  3. **Recommended Repairs**
     - Step-by-step procedures
     - Estimated costs (parts + labor)
     - Difficulty rating
     - Tools needed
     - Time estimate
  
  4. **Parts & Pricing**
     - Parts list table
     - Unit prices (min/max)
     - Total parts cost
     - Labor hours calculation
     - Total cost estimate
  
  5. **Supporting Information**
     - Related recalls
     - Known complaints
     - Information sources
     - Confidence metrics

- **Features:**
  - Export to PDF
  - Share diagnosis link
  - Save to history
  - Print-friendly view
  - Streaming real-time updates (during analysis)

#### Demo Result Page
- **URL:** `/demo`
- **Purpose:** Show sample diagnosis without login
- **Features:**
  - Pre-filled Volkswagen Golf example
  - Full result visualization
  - Call-to-action to run own diagnosis
  - Read-only view

#### History Page (Private)
- **URL:** `/history`
- **Features:**
  - Table of past diagnoses
  - Pagination (20 items per page)
  - Filters:
    - Date range
    - Vehicle make/model
    - DTC code
    - Cost range
  - Sorting:
    - By date (newest first)
    - By vehicle
    - By confidence score
  - Stats:
    - Total diagnoses run
    - Average confidence
    - Cost distribution
    - Most common DTCs
    - Most common vehicles
  
- **Actions:**
  - View full result
  - Re-run diagnosis
  - Delete diagnosis
  - Export report

#### DTC Detail Page
- **URL:** `/dtc/{code}`
- **Features:**
  - Full DTC information
  - English + Hungarian descriptions
  - Symptoms list
  - Possible causes
  - Diagnostic procedures
  - Related codes
  - Vehicles most affected
  - Similar codes

#### Login Page
- **URL:** `/login`
- **Features:**
  - Email and password fields
  - "Remember me" checkbox
  - "Forgot password" link
  - Social login future-ready
  - Form validation

#### Register Page
- **URL:** `/register`
- **Features:**
  - Email, password, confirm password
  - Full name field
  - Password strength meter
  - Terms acceptance checkbox
  - Link to login page

#### Password Reset Pages
- **Forgot Password:** `/forgot-password`
- **Reset Password:** `/reset-password/{token}`
- **Features:** Email input, new password, confirmation

### 3.2 Components Library

#### UI Components (lib/)
- **Button** - Primary, secondary, outline variants
- **Card** - Container for content grouping
- **Input** - Text input with validation states
- **Select** - Dropdown selection
- **Textarea** - Multi-line text input
- **Badge** - Status and tag display
- **ErrorMessage** - Error state display
- **LoadingSpinner** - Loading indicator

#### Feature Components (features/)

**Diagnosis Components:**
- `DiagnosisForm` - Main input form with 4-step wizard
- `AnalysisProgress` - Real-time streaming progress indicator
- `DiagnosticConfidence` - Confidence score visualization
- `CostEstimate` - Parts + labor pricing breakdown
- `PartsList` - Table of parts with pricing
- `PartStoreCard` - Links to part stores
- `RepairStep` - Step-by-step repair procedure
- `RecentAnalysisList` - Quick-access to past diagnoses
- `AIDisclaimerBadge` - AI disclaimer badge

**History Components:**
- `HistoryTable` - Paginated diagnosis history
- `HistoryFilterBar` - Filter and search controls
- `HistoryStats` - Statistics cards (count, avg, etc.)

#### Layout Components
- `Header` - Navigation bar with user menu
- `PageContainer` - Standard page wrapper
- `FloatingBottomBar` - Bottom action bar (mobile)
- `Layout` - App shell with header/footer

#### Composite Components
- `WizardStepper` - Multi-step form stepper
- `SearchInput` - Search field with debounce
- `StatCard` - Metric display card
- `Table` - Data table with sorting/pagination
- `Pagination` - Page navigation

#### Utility Components
- `VehicleSelector` - Make/model/year picker
- `DTCAutocomplete` - DTC code suggestions
- `MaterialIcon` - Icon component wrapper
- `PasswordStrengthMeter` - Password quality indicator
- `ErrorBoundary` - Error boundary for React
- `SectionErrorBoundary` - Section-level error handling

### 3.3 State Management & Data Fetching

#### React Query (TanStack Query)
- **Caching:** Automatic request deduplication
- **Refetching:** Smart background updates
- **Infinite Queries:** Pagination for large lists
- **Mutations:** Diagnosis submission handling

#### API Services
- `api.ts` - Base HTTP client (Axios)
- `diagnosisService.ts` - Diagnosis API calls
- `dtcService.ts` - DTC code API calls
- `vehicleService.ts` - Vehicle API calls
- `authService.ts` - Authentication API calls

#### Custom Hooks
- `useDiagnosis()` - Diagnosis operations
- `useDTC()` - DTC search and detail
- `useVehicle()` - Vehicle operations
- `useVehicles()` - Vehicle list with pagination

#### Context Providers
- `AuthContext` - User authentication state
- `ToastContext` - Notification system

### 3.4 Frontend Technology Stack

#### Core Libraries
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool (lightning-fast)
- **React Router v6** - Client-side routing
- **TanStack Query v5** - Server state management

#### Styling
- **TailwindCSS v3** - Utility-first CSS
- **Lucide React** - Icon library
- **Tailwind Merge** - CSS class merging

#### Form Management
- **React Hook Form** - Form state
- **Zod** - Runtime validation
- **@hookform/resolvers** - Validation integration

#### HTTP & Async
- **Axios** - HTTP client
- **React Router Navigation** - Client routing

#### Testing & Quality
- **Vitest** - Unit testing
- **@testing-library/react** - Component testing
- **Sentry** - Error tracking and monitoring
- **ESLint** - Code linting

#### Development
- **TypeScript** - Static type checking
- **Vite plugins** - Build optimization
- **Hot Module Replacement** - Dev server

---

## Section 4: Technical Architecture

### 4.1 Backend Tech Stack

#### Core Framework
- **FastAPI** v0.109.2 - High-performance async web framework
- **Pydantic v2** - Data validation and serialization
- **Python 3.11+** - Runtime (3.9 compatible)
- **Uvicorn** - ASGI server

#### Databases

**PostgreSQL 16**
- Structured data (users, diagnosis history, DTC codes)
- SQLAlchemy 2.0 ORM with async support
- Alembic migrations
- JSONB columns for flexible data
- Array columns for lists

**Neo4j 5.x**
- Knowledge graph (vehicles, DTCs, symptoms, components, repairs)
- Cypher query language
- APOC plugins for advanced queries
- 26,816 nodes, relationships for diagnostic paths

**Qdrant**
- Vector database for semantic search
- 768-dimensional embeddings
- cosine similarity search
- 35,000+ indexed vectors

**Redis 7**
- Session storage
- Cache layer (1-24 hour TTL)
- Tokens blacklist
- Rate limiting state

#### ORM & Database Tools
- **SQLAlchemy 2.0** - Async ORM
- **asyncpg** - PostgreSQL async driver
- **Alembic** - Database migrations
- **neomodel** - Neo4j ORM
- **qdrant-client** - Vector DB Python client

#### Authentication & Security
- **PyJWT** - JWT token creation/validation
- **Passlib + Bcrypt** - Password hashing
- **Python-multipart** - Form data parsing

#### AI/ML Stack
- **LangChain** - RAG orchestration
- **Anthropic Claude API** - Primary LLM
- **OpenAI GPT-4** - Fallback LLM
- **Transformers** - huBERT model
- **Sentence-Transformers** - Embedding generation
- **Torch** - Deep learning framework

#### NLP
- **huBERT (SZTAKI-HLT)** - Hungarian BERT embeddings
- **HuSpaCy** - Hungarian linguistic processing (optional)
- **Transformers** - Model loading and inference

#### External APIs
- **NHTSA vPIC API** - VIN decoding
- **NHTSA Complaints API** - Consumer complaints
- **NHTSA Recalls API** - Vehicle recalls

#### HTTP & Async
- **httpx** - Async HTTP client
- **aiohttp** - Async requests
- **Requests** - Sync HTTP (for compatibility)

#### Monitoring & Logging
- **Prometheus** - Metrics collection
- **Structured logging** - JSON-formatted logs
- **Python logging** - Standard library

#### Deployment
- **Docker** - Containerization
- **Gunicorn** - Production WSGI server
- **Railway** - PaaS deployment
- **GitHub Actions** - CI/CD

#### Data Processing
- **Pandas** - Data analysis
- **NumPy** - Numerical computing

### 4.2 Frontend Tech Stack

**Already detailed in Section 3.4**

### 4.3 Infrastructure

#### Deployment Architecture
```
┌─────────────────────────────────────────────┐
│            Railway Platform                  │
├─────────────────────────────────────────────┤
│ Frontend (React) ← Vite Build              │
│ Backend (FastAPI) ← Uvicorn                │
│ PostgreSQL (Railway)                        │
│ Redis (Railway)                             │
└─────────────────────────────────────────────┘
         │
         ├─→ Neo4j Aura (Cloud)
         ├─→ Qdrant Cloud (Vector DB)
         └─→ NHTSA API (External)
```

#### Docker Compose Services
1. **PostgreSQL 16** - Relational data
2. **Neo4j 5.15** - Graph database
3. **Qdrant** - Vector search
4. **Redis 7** - Cache/sessions
5. **FastAPI Backend** - API server
6. **React Frontend** - Web UI
7. **Prometheus** (optional) - Metrics
8. **Grafana** (optional) - Dashboards

#### Storage & Caching
- **PostgreSQL**: Users, diagnosis sessions, DTC codes
- **Neo4j**: Vehicle graph, diagnostic paths
- **Qdrant**: Embeddings for semantic search
- **Redis**: Cache (DTC lookups, search results)
- **Docker Volumes**: Data persistence

### 4.4 API Architecture

#### RESTful Design
- Base URL: `/api/v1`
- Standard HTTP methods
- JSON request/response bodies
- Pydantic schemas for validation
- OpenAPI/Swagger documentation

#### Authentication
- JWT tokens in Authorization header
- httpOnly cookies for security
- Token refresh mechanism
- CORS enabled for cross-origin

#### Error Handling
- Standard HTTP status codes
- Detailed error messages
- Validation error responses
- Rate limiting (60 req/min, 1000 req/hour)

#### Performance
- Response compression
- Redis caching layer
- Async database operations
- Connection pooling
- Query optimization

---

## Section 5: Key Unique Features & Differentiators

### 5.1 What Makes AutoCognitix Different

#### 1. Hungarian Language-First Approach
- Native Hungarian UI and prompts
- huBERT embeddings (Hungarian-optimized BERT)
- Hungarian DTC descriptions
- Symptom recognition in Hungarian

#### 2. Hardware-Free Diagnosis
- No OBD-II scanner required
- Manual DTC code input
- Text-based symptom description
- Works on any device with browser

#### 3. Knowledge Graph Integration
- Symptoms → DTCs → Components → Repairs
- Pathfinding for diagnostic procedures
- Relationship mapping between issues
- Neo4j-powered connectivity

#### 4. RAG (Retrieval-Augmented Generation)
- Multi-source context retrieval
- Hybrid search (semantic + keyword)
- Confidence scoring
- Citation of sources

#### 5. Real-Time Streaming
- Server-Sent Events for live updates
- Progressive diagnosis display
- Real-time confidence updates
- User sees AI "thinking"

#### 6. Comprehensive Cost Estimation
- Parts pricing (min/max/average)
- Labor cost by difficulty
- Total cost calculation
- HUF currency for Hungarian users

#### 7. NHTSA Integration
- Live recall lookup
- Consumer complaint database
- Safety history for any vehicle
- Real-time data from official sources

#### 8. Vector-Powered Search
- Semantic similarity matching
- Find related issues even with different wording
- 768-dimensional embeddings
- No API rate limits (local model)

### 5.2 Competitive Advantages

| Feature | AutoCognitix | Typical Competitors |
|---------|------------------|-----|
| Language | Hungarian + English | English only |
| Hardware Required | None | OBD-II scanner |
| Cost | Free/Freemium | $$$-$$$$ |
| Vector Search | Yes (Qdrant) | No |
| Knowledge Graph | Yes (Neo4j) | Flat database |
| Real-time Streaming | Yes (SSE) | Static results |
| NHTSA Integration | Yes (live) | Cached data |
| Parts Pricing | Yes | Manual research |
| Open Source | Yes | Proprietary |
| AI Model | Claude/GPT-4 | Custom/proprietary |

---

## Section 6: Data Schema & Storage

### 6.1 PostgreSQL Schema

#### Users Table
- id (UUID)
- email (unique)
- hashed_password
- full_name
- role (user/mechanic/admin)
- is_active, is_superuser
- Account security fields (failed_login_attempts, locked_until)
- Email verification fields
- Timestamps (created_at, updated_at, last_login_at)

#### DTC Codes Table
- id (primary key)
- code (unique, indexed) - "P0101", "B1234", etc.
- description_en, description_hu
- category (powertrain/body/chassis/network)
- severity (low/medium/high/critical)
- is_generic (boolean)
- system, symptoms, possible_causes, diagnostic_steps (arrays)
- related_codes, applicable_makes (arrays)
- sources, manufacturer_code
- Timestamps

#### Diagnosis Sessions Table
- id (UUID)
- user_id (foreign key)
- vehicle_make, vehicle_model, vehicle_year
- dtc_codes (array)
- symptoms (text)
- vin, engine_code (optional)
- analysis (JSONB) - Full AI response
- cost_estimate (JSONB) - Parts + labor
- confidence_score
- processing_time_ms
- Timestamps

#### Known Issues Table
- id (primary key)
- title, description
- symptoms, causes, solutions (arrays)
- related_dtc_codes, applicable_makes/models (arrays)
- year_start, year_end
- confidence, source_type, source_url
- Timestamps

#### Vehicle Makes/Models
- VehicleMake: id, name, country, logo_url, nhtsa_make_id
- VehicleModel: id, name, make_id, year_start, year_end, body_types, engine_codes

### 6.2 Neo4j Schema

#### Node Types
- **Make** - Vehicle manufacturer
- **Model** - Vehicle model
- **Year** - Model year
- **DTC** - Diagnostic trouble code
- **Symptom** - User-facing symptom
- **Component** - Vehicle component
- **Repair** - Repair procedure
- **TSB** - Technical service bulletin
- **Recall** - Safety recall
- **Complaint** - Consumer complaint

#### Relationships
```
(Make)-[:HAS_MODEL]->(Model)
(Model)-[:PRODUCED_IN]->(Year)
(Make,Model,Year)-[:HAS_COMMON_DTC]->(DTC)
(DTC)-[:CAUSES]->(Symptom)
(DTC)-[:AFFECTS]->(Component)
(Component)-[:REQUIRES]->(Repair)
(Repair)-[:NEEDS]->(Part)
(DTC)-[:RELATED_TO]->(DTC)
(DTC)-[:MENTIONED_IN]->(TSB)
(Make,Model,Year)-[:HAS_RECALL]->(Recall)
(Make,Model,Year)-[:HAS_COMPLAINT]->(Complaint)
```

#### Properties
- All nodes: name, description_hu, description_en, created_at
- DTCs: code, category, severity, is_generic
- Parts: price_min, price_max, labor_hours
- Symptoms: frequency_score, severity_level
- Repairs: difficulty, estimated_time_minutes

### 6.3 Qdrant Vector Storage

#### Collections
- **dtc_embeddings** - DTC code descriptions (768-dim)
- **symptom_embeddings** - Symptom descriptions
- **known_issue_embeddings** - Known issue descriptions

#### Vector Points
```json
{
  "id": 1,
  "vector": [0.123, 0.456, ..., 0.789],  // 768 dimensions
  "payload": {
    "text": "Levegotomeg-mero aramkor hibas",
    "code": "P0101",
    "type": "dtc",
    "category": "powertrain"
  }
}
```

#### Search Method
- Cosine similarity
- Top-K retrieval (k=5-10)
- Hybrid filtering with metadata

---

## Section 7: API Endpoints Summary

### 7.1 Authentication Endpoints
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/refresh` - Refresh access token
- `GET /auth/profile` - Get user profile
- `PUT /auth/profile` - Update user profile
- `POST /auth/change-password` - Change password
- `POST /auth/forgot-password` - Request password reset
- `POST /auth/reset-password` - Reset password with token

### 7.2 Diagnosis Endpoints
- `POST /diagnosis/analyze` - Run diagnosis (standard)
- `POST /diagnosis/analyze-stream` - Run diagnosis (streaming)
- `GET /diagnosis/{id}` - Get diagnosis result
- `GET /diagnosis/history` - List user's diagnoses
- `DELETE /diagnosis/{id}` - Delete diagnosis

### 7.3 DTC Endpoints
- `GET /dtc/search` - Search DTC codes
- `GET /dtc/{code}` - Get DTC details
- `GET /dtc/{code}/related` - Get related codes
- `GET /dtc/categories` - List DTC categories

### 7.4 Vehicle Endpoints
- `GET /vehicles/makes` - List vehicle manufacturers
- `GET /vehicles/models` - List models for make
- `GET /vehicles/years` - Get available years
- `POST /vehicles/decode-vin` - Decode VIN
- `GET /vehicles/{make}/{model}/{year}/recalls` - Get recalls
- `GET /vehicles/{make}/{model}/{year}/complaints` - Get complaints
- `GET /vehicles/{make}/{model}/common-issues` - Get common issues

### 7.5 Health & Metrics
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /metrics/diagnosis` - Diagnosis statistics

---

## Section 8: User Flows & Workflows

### 8.1 Diagnosis Workflow

1. **Home Page** → User clicks "Diagnózis indítása" or "Demo megtekintése"
2. **New Diagnosis Page** → Form appears with:
   - DTC code input (autocomplete)
   - Symptom text area
   - Vehicle selector (make/model/year dropdown)
   - Optional VIN input
3. **Validation** → Client-side validation with error display
4. **Submission** → Form POSTs to `/api/v1/diagnosis/analyze`
5. **Streaming** → If streaming, SSE connection shows progress
6. **Results** → Result page shows:
   - Input summary
   - Probable causes (ranked by confidence)
   - Recommended repairs
   - Parts list with pricing
   - Related recalls
7. **Actions** → User can:
   - Export to PDF
   - Share diagnosis link
   - View related DTCs
   - Run new diagnosis

### 8.2 Vehicle Lookup Workflow

1. User selects vehicle: Make → Model → Year
2. System queries Neo4j for:
   - All models of selected make
   - All years for model
   - Common issues for combination
3. Optional: Decode VIN to auto-fill details
4. System fetches from NHTSA:
   - Recalls for vehicle
   - Consumer complaints
   - Safety history

### 8.3 Authentication Workflow

**Registration:**
1. User fills registration form
2. Submit → Backend validates
3. User created in PostgreSQL
4. Email verification optional
5. User auto-logged in with JWT tokens
6. Redirects to diagnosis page

**Login:**
1. User enters email/password
2. Backend validates credentials
3. Tokens generated (access + refresh)
4. Stored in httpOnly cookies
5. Redirects to dashboard

**Forgot Password:**
1. User enters email
2. Backend sends reset link
3. User clicks link in email
4. Form to enter new password
5. Token validated, password updated
6. User can login with new password

### 8.4 History Browsing Workflow

1. User navigates to History page
2. System loads paginated list of diagnoses
3. User can:
   - Filter by date, vehicle, cost range
   - Sort by date, vehicle, confidence
   - Search for specific DTC code
4. Click on diagnosis to view results
5. Options to:
   - Re-run same diagnosis
   - Export report
   - Delete record

---

## Section 9: Deployment & Infrastructure

### 9.1 Local Development

**Requirements:**
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
- Git

**Quick Start:**
```bash
git clone https://github.com/norbertbarna/AutoCognitix.git
cd AutoCognitix
cp .env.example .env
docker-compose up -d
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
# Neo4j: http://localhost:7474
```

### 9.2 Production Deployment (Railway)

**Architecture:**
- Railway manages PostgreSQL + Redis
- FastAPI backend deployed as service
- React frontend deployed as service
- Neo4j Aura (Cloud) for graph DB
- Qdrant Cloud for vector DB

**Deployment Process:**
1. Push to GitHub main branch
2. GitHub Actions triggers CD workflow
3. Docker images built for amd64/arm64
4. Pushed to GitHub Container Registry
5. Railway auto-deploys from registry
6. Smoke tests verify health
7. Auto-rollback on failure

**Environment Variables Required:**
```
DATABASE_URL=postgresql://...
NEO4J_URI=neo4j+s://xxx.databases.neo4j.io
NEO4J_PASSWORD=...
QDRANT_URL=https://xxx.cloud.qdrant.io:6333
QDRANT_API_KEY=...
ANTHROPIC_API_KEY=...
JWT_SECRET_KEY=...
```

### 9.3 Database Cloud Services

**PostgreSQL:** Railway-managed
- 16GB storage (free tier)
- Automated backups
- Connection pooling

**Neo4j Aura:** Free tier
- Fully managed Neo4j instance
- 4GB storage
- High availability

**Qdrant Cloud:** Free tier
- Vector search
- 1GB storage
- No rate limits

**Redis:** Railway-managed
- Caching layer
- Session storage
- 256MB (free tier)

---

## Section 10: Future Roadmap & Extensibility

### 10.1 Planned Features

1. **Mobile App**
   - iOS/Android native apps
   - Camera-based VIN scanning
   - Offline mode
   - Push notifications

2. **Enhanced AI**
   - Multiple language support (German, French, Spanish)
   - Voice input for symptoms
   - Image-based component identification
   - Predictive maintenance

3. **Workshop Integration**
   - Workshop dashboard
   - Team collaboration
   - Parts ordering integration
   - Invoice generation

4. **Premium Features**
   - Advanced analytics
   - Workshop tools
   - Integration with parts suppliers
   - Technical support access

### 10.2 API Extensibility

#### Third-Party Integration Points
- **Parts Supplier APIs** - eBay, Amazon, local suppliers
- **Repair Shop APIs** - Connect with local mechanics
- **OBD-II Scanner APIs** - For hardware connectivity
- **CRM Integration** - Salesforce, HubSpot compatibility

#### Custom LLM Support
- Ollama integration
- Local LLM deployment
- Custom prompt templates
- Fine-tuning on domain data

#### Data Export
- PDF reports
- CSV analytics
- JSON API responses
- Integration webhooks

---

## Section 11: Security & Compliance

### 11.1 Security Features

- **Authentication:** JWT tokens with expiration
- **Password Security:** Bcrypt hashing
- **Account Lockout:** After failed attempts
- **Input Validation:** Pydantic schemas
- **SQL Injection Prevention:** Parameterized queries (SQLAlchemy)
- **CSRF Protection:** SameSite cookies
- **CORS:** Configured for frontend domain
- **Rate Limiting:** 60 req/min per user
- **HTTPS:** Enforced in production
- **Secret Management:** Environment variables
- **Dependency Scanning:** Dependabot alerts
- **Code Scanning:** GitHub CodeQL

### 11.2 Data Privacy

- **User Data:** Encrypted in transit (TLS)
- **Sensitive Fields:** Bcrypt hashed (passwords)
- **Session Data:** Redis with TTL
- **Diagnosis History:** Owned by users
- **GDPR Compliance:** Data export/deletion available
- **No Analytics Tracking:** Except Sentry error logs

### 11.3 Compliance

- **Open Source:** Proprietary license
- **Code Quality:** Ruff linting, MyPy type checking
- **Testing:** pytest + Vitest coverage
- **CI/CD:** GitHub Actions automation

---

## Section 12: Performance Metrics & Optimization

### 12.1 Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time | <500ms | ~300ms |
| Diagnosis Analysis | <30s | ~10-20s |
| Page Load Time | <2s | ~1.5s |
| Vector Search | <100ms | ~50ms |
| Database Query | <50ms | ~20ms |

### 12.2 Optimization Techniques

1. **Database Optimization**
   - Connection pooling
   - Query caching (Redis)
   - Indexed columns
   - Async database operations

2. **Frontend Optimization**
   - Code splitting with Vite
   - Lazy loading components
   - Image optimization
   - TanStack Query caching

3. **API Optimization**
   - Response compression
   - JSON serialization optimization
   - Async operations
   - Rate limiting

4. **Search Optimization**
   - Vector similarity caching
   - Hybrid search indexing
   - Query parameter validation

---

## Section 13: Testing & Quality Assurance

### 13.1 Test Coverage

**Backend:**
- Unit tests: pytest
- API tests: FastAPI TestClient
- Integration tests: Docker containers
- Coverage target: >80%

**Frontend:**
- Component tests: @testing-library/react
- Unit tests: Vitest
- E2E tests: (future - Playwright)
- Coverage target: >75%

### 13.2 CI/CD Pipeline

**Continuous Integration (on push/PR):**
- Ruff linting
- MyPy type checking
- pytest with coverage
- ESLint + TypeScript check
- Docker build verification

**Continuous Deployment (on tag/release):**
- Multi-platform Docker build
- Push to GHCR
- Railway deployment
- Health checks
- Smoke tests
- Auto-rollback

### 13.3 Monitoring & Observability

- **Prometheus:** Metrics collection
- **Grafana:** Dashboards
- **Sentry:** Error tracking
- **Structured Logs:** JSON-formatted
- **Health Checks:** `/health` endpoint

---

## Section 14: Support & Documentation

### 14.1 Available Documentation

1. **API Documentation**
   - Swagger UI: `/api/v1/docs`
   - ReDoc: `/api/v1/redoc`
   - OpenAPI JSON: `/api/v1/openapi.json`

2. **User Manual**
   - Hungarian User Manual
   - Video tutorials (planned)
   - FAQ section

3. **Developer Documentation**
   - Installation guide
   - Development guide
   - API reference
   - Architecture documentation
   - Deployment guide

4. **Technical References**
   - Database schema
   - File structure
   - API endpoints
   - Error codes

### 14.2 Support Channels

- GitHub Issues: Bug reports & feature requests
- Email: support@autocognitix.hu (future)
- Discord: Community support (future)
- Email: contact@norbertbarna.hu (maintainer)

---

## Section 15: Licensing & Open Source

### 15.1 Project Status

- **Repository:** https://github.com/norbertbarna/AutoCognitix
- **License:** Proprietary (see LICENSE file)
- **Status:** Production-ready
- **Version:** 0.1.0 (pre-release)

### 15.2 Contributing

- Fork the repository
- Create feature branch
- Follow code standards (Ruff, MyPy)
- Add tests
- Submit pull request
- Community contributions welcome

### 15.3 Third-Party Licenses

- FastAPI: MIT
- React: MIT
- TailwindCSS: MIT
- SQLAlchemy: MIT
- Neo4j: GPL/Community
- Qdrant: AGPL-3.0

---

## Summary: Key Metrics for Landing Page

### AutoCognitix By The Numbers

- **3 Databases:** PostgreSQL, Neo4j, Qdrant
- **50+ Endpoints:** Comprehensive REST API
- **63+ DTC Codes:** Diagnostic database
- **8,145+ Vehicles:** Make/model/year combinations
- **26,816 Graph Nodes:** Neo4j knowledge graph
- **35,000+ Vectors:** Qdrant embeddings
- **2 Languages:** Hungarian & English
- **0 Hardware:** Required for diagnosis
- **5 Components:** React, FastAPI, PostgreSQL, Neo4j, Qdrant
- **Zero Rate Limits:** On vector search (local model)
- **Production Deployed:** On Railway
- **Open Source:** GitHub repository
- **100% API Documented:** Swagger + ReDoc

---

## Call-to-Action Statements for Landing Page

1. **"Gyors, pontós diagnózis mesterséges intelligenciával"**
   *(Fast, accurate diagnosis with artificial intelligence)*

2. **"Nem szükséges OBD-II szkenner - csak egy böngésző"**
   *(No OBD-II scanner needed - just a browser)*

3. **"Magyar nyelvű, teljes körű autódiagnosztika"**
   *(Complete vehicle diagnostics in Hungarian language)*

4. **"AI-alapú megoldás szerelőknek és gépkocsi-tulajdonosoknak"**
   *(AI-powered solution for mechanics and car owners)*

5. **"Alkatrészárak, javítási költségbecslés, biztonsági riasztások"**
   *(Parts pricing, repair cost estimates, safety alerts)*

---

