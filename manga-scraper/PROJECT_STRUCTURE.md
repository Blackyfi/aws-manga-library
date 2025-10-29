# Project Structure - Manga Scraper

## 📁 Complete Directory Tree

```
C:\Users\Nicolas\Documents\git\aws-manga-library/manga-scraper/
├── .github/
│   └── workflows/
│       ├── ci.yml                          # CI/CD pipeline configuration
│       ├── deploy-lambda.yml               # Lambda deployment workflow
│       └── test.yml                        # Automated testing workflow
│
├── scraper/                                # Python scraping backend
│   ├── src/
│   │   ├── __init__.py                    # Package initialization
│   │   ├── manga_scraper.py               # Main scraper implementation
│   │   ├── config.py                      # Configuration management
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── manga.py                   # Manga data models
│   │   │   └── chapter.py                 # Chapter data models
│   │   ├── processors/
│   │   │   ├── __init__.py
│   │   │   ├── image_processor.py         # Image optimization
│   │   │   └── duplicate_detector.py      # Hash-based deduplication
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── base_scraper.py           # Abstract base scraper
│   │   │   ├── mangadex_scraper.py       # MangaDex implementation
│   │   │   └── mangakakalot_scraper.py   # MangaKakalot implementation
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   ├── s3_storage.py             # S3 operations
│   │   │   └── dynamodb_manager.py       # DynamoDB operations
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── rate_limiter.py           # Rate limiting logic
│   │       ├── retry_handler.py          # Retry with backoff
│   │       └── logger.py                 # Logging configuration
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py                    # pytest configuration
│   │   ├── test_manga_scraper.py          # Main scraper tests
│   │   ├── test_image_processor.py        # Image processing tests
│   │   ├── test_storage.py                # Storage tests
│   │   ├── fixtures/
│   │   │   ├── sample_images/             # Test images
│   │   │   └── mock_responses/            # Mock HTML responses
│   │   └── integration/
│   │       ├── test_end_to_end.py        # E2E tests
│   │       └── test_aws_integration.py    # AWS integration tests
│   │
│   ├── lambda/
│   │   ├── handler.py                     # Lambda entry point
│   │   └── requirements.txt               # Lambda-specific dependencies
│   │
│   ├── scripts/
│   │   ├── setup_aws.sh                   # AWS resource setup script
│   │   ├── deploy.sh                      # Deployment script
│   │   └── example_usage.py               # Usage examples
│   │
│   ├── requirements.txt                    # Python dependencies
│   ├── requirements-dev.txt                # Development dependencies
│   ├── setup.py                           # Package installation
│   ├── pyproject.toml                     # Python project config
│   ├── .pylintrc                          # Pylint configuration
│   ├── .flake8                            # Flake8 configuration
│   └── mypy.ini                           # MyPy configuration
│
├── frontend/                               # Next.js frontend application
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                 # Root layout
│   │   │   ├── page.tsx                   # Home page
│   │   │   ├── globals.css                # Global styles
│   │   │   ├── manga/
│   │   │   │   ├── page.tsx              # Manga library page
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx          # Manga detail page
│   │   │   │       └── [chapter]/
│   │   │   │           └── page.tsx      # Chapter reader page
│   │   │   ├── search/
│   │   │   │   └── page.tsx              # Search page
│   │   │   └── api/
│   │   │       ├── manga/
│   │   │       │   └── route.ts          # Manga API routes
│   │   │       └── chapters/
│   │   │           └── route.ts          # Chapter API routes
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Header.tsx            # Site header
│   │   │   │   ├── Footer.tsx            # Site footer
│   │   │   │   └── Navigation.tsx        # Navigation menu
│   │   │   ├── manga/
│   │   │   │   ├── MangaCard.tsx         # Manga card component
│   │   │   │   ├── MangaGrid.tsx         # Manga grid layout
│   │   │   │   ├── MangaDetail.tsx       # Manga details view
│   │   │   │   └── ChapterList.tsx       # Chapter listing
│   │   │   ├── reader/
│   │   │   │   ├── MangaReader.tsx       # Main reader component
│   │   │   │   ├── PageViewer.tsx        # Page display
│   │   │   │   ├── ReaderControls.tsx    # Reader controls
│   │   │   │   └── ProgressTracker.tsx   # Reading progress
│   │   │   ├── common/
│   │   │   │   ├── Button.tsx            # Reusable button
│   │   │   │   ├── Card.tsx              # Card component
│   │   │   │   ├── Loading.tsx           # Loading spinner
│   │   │   │   └── ErrorBoundary.tsx     # Error handling
│   │   │   └── ui/
│   │   │       ├── dialog.tsx            # Dialog component
│   │   │       ├── dropdown.tsx          # Dropdown menu
│   │   │       └── toast.tsx             # Toast notifications
│   │   │
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── manga.ts              # Manga API client
│   │   │   │   └── chapters.ts           # Chapter API client
│   │   │   ├── hooks/
│   │   │   │   ├── useManga.ts           # Manga data hook
│   │   │   │   ├── useChapter.ts         # Chapter data hook
│   │   │   │   └── useProgress.ts        # Progress tracking hook
│   │   │   ├── store/
│   │   │   │   ├── index.ts              # Store configuration
│   │   │   │   ├── mangaStore.ts         # Manga state management
│   │   │   │   └── userStore.ts          # User preferences
│   │   │   └── utils/
│   │   │       ├── formatters.ts         # Data formatters
│   │   │       ├── validators.ts         # Input validation
│   │   │       └── storage.ts            # localStorage helpers
│   │   │
│   │   └── types/
│   │       ├── manga.ts                   # TypeScript types for manga
│   │       ├── chapter.ts                 # TypeScript types for chapters
│   │       └── api.ts                     # API response types
│   │
│   ├── public/
│   │   ├── images/
│   │   │   ├── logo.svg                   # Site logo
│   │   │   └── placeholder.jpg            # Placeholder image
│   │   └── fonts/                         # Custom fonts
│   │
│   ├── tests/
│   │   ├── components/
│   │   │   ├── MangaCard.test.tsx        # Component tests
│   │   │   └── MangaReader.test.tsx
│   │   ├── pages/
│   │   │   └── index.test.tsx            # Page tests
│   │   └── lib/
│   │       └── api.test.ts               # API tests
│   │
│   ├── .eslintrc.json                     # ESLint configuration
│   ├── .prettierrc                        # Prettier configuration
│   ├── next.config.js                     # Next.js configuration
│   ├── tailwind.config.ts                 # Tailwind CSS config
│   ├── tsconfig.json                      # TypeScript configuration
│   ├── jest.config.js                     # Jest configuration
│   ├── package.json                       # Node dependencies
│   └── package-lock.json                  # Locked dependencies
│
├── infrastructure/                         # Infrastructure as Code
│   ├── terraform/
│   │   ├── main.tf                        # Main Terraform config
│   │   ├── variables.tf                   # Variable definitions
│   │   ├── outputs.tf                     # Output values
│   │   ├── modules/
│   │   │   ├── lambda/
│   │   │   │   ├── main.tf               # Lambda module
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   ├── s3/
│   │   │   │   ├── main.tf               # S3 module
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   ├── dynamodb/
│   │   │   │   ├── main.tf               # DynamoDB module
│   │   │   │   ├── variables.tf
│   │   │   │   └── outputs.tf
│   │   │   └── cloudfront/
│   │   │       ├── main.tf               # CloudFront module
│   │   │       ├── variables.tf
│   │   │       └── outputs.tf
│   │   │
│   │   ├── environments/
│   │   │   ├── dev/
│   │   │   │   ├── main.tf              # Dev environment
│   │   │   │   └── terraform.tfvars
│   │   │   ├── staging/
│   │   │   │   ├── main.tf              # Staging environment
│   │   │   │   └── terraform.tfvars
│   │   │   └── prod/
│   │   │       ├── main.tf              # Production environment
│   │   │       └── terraform.tfvars
│   │   │
│   │   └── backend.tf                    # Terraform backend config
│   │
│   └── cloudformation/                    # Alternative: CloudFormation
│       ├── lambda-stack.yaml
│       ├── storage-stack.yaml
│       └── network-stack.yaml
│
├── docs/                                   # Project documentation
│   ├── api/
│   │   ├── manga-endpoints.md            # Manga API documentation
│   │   └── chapter-endpoints.md          # Chapter API documentation
│   ├── architecture/
│   │   ├── system-design.md              # System architecture
│   │   ├── data-flow.md                  # Data flow diagrams
│   │   └── aws-infrastructure.md         # AWS setup guide
│   ├── guides/
│   │   ├── setup-guide.md                # Setup instructions
│   │   ├── deployment-guide.md           # Deployment steps
│   │   ├── contributing.md               # Contribution guidelines
│   │   └── troubleshooting.md            # Common issues
│   ├── diagrams/
│   │   ├── architecture.png              # Architecture diagram
│   │   ├── data-flow.png                 # Data flow diagram
│   │   └── deployment.png                # Deployment diagram
│   └── screenshots/
│       ├── reader-view.png               # Reader interface
│       └── library-view.png              # Library interface
│
├── docker/                                 # Docker configuration
│   ├── Dockerfile.scraper                 # Scraper container
│   ├── Dockerfile.frontend                # Frontend container
│   └── docker-compose.yml                 # Local development setup
│
├── scripts/                                # Utility scripts
│   ├── setup/
│   │   ├── install-dependencies.sh       # Dependency installation
│   │   ├── create-aws-resources.sh       # AWS resource creation
│   │   └── init-database.sh              # Database initialization
│   ├── deploy/
│   │   ├── deploy-lambda.sh              # Lambda deployment
│   │   ├── deploy-frontend.sh            # Frontend deployment
│   │   └── rollback.sh                   # Rollback script
│   ├── maintenance/
│   │   ├── backup-database.sh            # Database backup
│   │   ├── clean-old-images.sh           # Cleanup old images
│   │   └── update-dependencies.sh        # Dependency updates
│   └── monitoring/
│       ├── check-health.sh               # Health check
│       └── generate-report.sh            # Usage report
│
├── .github/                                # GitHub configuration
│   ├── workflows/                         # GitHub Actions (see above)
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md                 # Bug report template
│   │   └── feature_request.md            # Feature request template
│   └── PULL_REQUEST_TEMPLATE.md          # PR template
│
├── .env.example                            # Environment variables template
├── .gitignore                              # Git ignore rules
├── .dockerignore                           # Docker ignore rules
├── .editorconfig                           # Editor configuration
├── LICENSE                                 # Project license
├── README.md                               # Project overview
├── CONTRIBUTING.md                         # Contribution guidelines
├── CHANGELOG.md                            # Version changelog
├── CODE_OF_CONDUCT.md                      # Code of conduct
├── SECURITY.md                             # Security policy
├── Makefile                                # Development automation
└── package.json                            # Root package.json (monorepo)
```

---

## 📂 Directory Descriptions

### `/scraper` - Backend Scraping Service

**Purpose**: Python-based scraping engine with AWS Lambda support

**Key Components**:
- `src/`: Core scraping logic and business code
- `tests/`: Comprehensive test suite (unit + integration)
- `lambda/`: AWS Lambda deployment package
- `scripts/`: Utility scripts for common tasks

**Technologies**: Python 3.11+, Boto3, BeautifulSoup4, Pillow

---

### `/frontend` - Next.js Web Application

**Purpose**: Modern, responsive manga reading interface

**Key Components**:
- `src/app/`: Next.js 14+ App Router pages
- `src/components/`: React components (layout, manga, reader, UI)
- `src/lib/`: Utilities, hooks, API clients, state management
- `tests/`: Jest + React Testing Library tests

**Technologies**: Next.js 14, TypeScript 5, Tailwind CSS, Zustand

---

### `/infrastructure` - Infrastructure as Code

**Purpose**: Automated AWS resource provisioning

**Key Components**:
- `terraform/`: Terraform configurations by resource and environment
- `cloudformation/`: Alternative CloudFormation templates

**Technologies**: Terraform, AWS CloudFormation

---

### `/docs` - Project Documentation

**Purpose**: Comprehensive project documentation

**Key Components**:
- `api/`: API endpoint documentation
- `architecture/`: System design documents
- `guides/`: Setup, deployment, and contribution guides
- `diagrams/`: Visual architecture representations

---

### `/docker` - Containerization

**Purpose**: Docker configuration for local development and deployment

**Key Components**:
- `Dockerfile.scraper`: Scraper service container
- `Dockerfile.frontend`: Frontend application container
- `docker-compose.yml`: Multi-container orchestration

---

### `/scripts` - Automation Scripts

**Purpose**: Automation for setup, deployment, and maintenance

**Key Components**:
- `setup/`: Initial setup and configuration
- `deploy/`: Deployment automation
- `maintenance/`: Ongoing maintenance tasks
- `monitoring/`: Health checks and reporting

---

### `/.github` - GitHub Configuration

**Purpose**: GitHub-specific configurations and workflows

**Key Components**:
- `workflows/`: CI/CD pipeline definitions
- Issue and PR templates
- Community health files

---

## 📄 Key Configuration Files

### Root Level

| File | Purpose |
|------|---------|
| `.env.example` | Template for environment variables |
| `.gitignore` | Git exclusion patterns |
| `.dockerignore` | Docker build exclusions |
| `.editorconfig` | Cross-editor configuration |
| `Makefile` | Development task automation |
| `README.md` | Project overview and quick start |
| `LICENSE` | Software license |
| `CHANGELOG.md` | Version history |

### Scraper (`/scraper`)

| File | Purpose |
|------|---------|
| `requirements.txt` | Python production dependencies |
| `requirements-dev.txt` | Python development dependencies |
| `setup.py` | Python package configuration |
| `pyproject.toml` | Modern Python project config |
| `.pylintrc` | Pylint linting rules |
| `.flake8` | Flake8 linting rules |
| `mypy.ini` | MyPy type checking config |

### Frontend (`/frontend`)

| File | Purpose |
|------|---------|
| `package.json` | Node.js dependencies and scripts |
| `tsconfig.json` | TypeScript compiler configuration |
| `next.config.js` | Next.js framework configuration |
| `tailwind.config.ts` | Tailwind CSS configuration |
| `.eslintrc.json` | ESLint linting rules |
| `.prettierrc` | Prettier formatting rules |
| `jest.config.js` | Jest testing configuration |

### Infrastructure (`/infrastructure`)

| File | Purpose |
|------|---------|
| `main.tf` | Main Terraform configuration |
| `variables.tf` | Input variable definitions |
| `outputs.tf` | Output value definitions |
| `backend.tf` | Terraform state backend |
| `terraform.tfvars` | Variable values by environment |

---

## 🗂️ File Naming Conventions

### Python Files
- **Snake case**: `manga_scraper.py`, `image_processor.py`
- **Test files**: `test_*.py` prefix for pytest discovery
- **Private modules**: `_internal.py` prefix for internal use

### TypeScript/React Files
- **PascalCase**: Components (`MangaCard.tsx`, `ReaderControls.tsx`)
- **camelCase**: Utilities (`formatters.ts`, `validators.ts`)
- **lowercase**: Routes (`route.ts`, `page.tsx`)
- **Test files**: `*.test.tsx` or `*.test.ts` suffix

### Configuration Files
- **Lowercase with dots**: `.eslintrc.json`, `.prettierrc`
- **Lowercase with hyphens**: `docker-compose.yml`
- **Uppercase**: `README.md`, `LICENSE`, `CHANGELOG.md`

---

## 📦 Module Organization

### Scraper Module Structure

```python
# scraper/src/manga_scraper.py
from .processors import ImageProcessor
from .storage import S3Storage, DynamoDBManager
from .utils import RateLimiter, RetryHandler
from .scrapers import MangaDexScraper

# Usage
scraper = MangaDexScraper()
processor = ImageProcessor()
storage = S3Storage('bucket-name')
```

### Frontend Module Structure

```typescript
// frontend/src/components/manga/MangaCard.tsx
import { useManga } from '@/lib/hooks/useManga'
import { Button } from '@/components/ui/button'
import { formatDate } from '@/lib/utils/formatters'

// Relative imports within same feature
import { ChapterList } from './ChapterList'
```

---

## 🔄 Data Flow Through Structure

```
User Request (Browser)
    ↓
frontend/src/app/manga/[id]/page.tsx
    ↓
frontend/src/lib/api/manga.ts
    ↓
AWS CloudFront (CDN Cache)
    ↓
AWS S3 (Images) + DynamoDB (Metadata)
    ↑
scraper/lambda/handler.py
    ↑
scraper/src/manga_scraper.py
    ↑
Target Manga Website
```

---

## 🚀 Deployment Structure

### Development Environment
```
Local Machine
├── Docker Compose (frontend + scraper)
├── Local DynamoDB
└── Mocked S3 (localstack)
```

### Staging Environment
```
AWS Staging
├── Lambda Function (scraper)
├── S3 Bucket (staging-manga-bucket)
├── DynamoDB Table (staging-manga-metadata)
└── CloudFront Distribution (staging CDN)
```

### Production Environment
```
AWS Production
├── Lambda Function (manga-scraper-prod)
├── S3 Bucket (prod-manga-bucket)
├── DynamoDB Table (prod-manga-metadata)
├── CloudFront Distribution (prod CDN)
└── EventBridge Rules (scheduled scraping)
```

---

## 📊 Size Estimates

| Directory | Estimated Size | File Count |
|-----------|----------------|------------|
| `/scraper` | ~50 KB | 25-30 files |
| `/frontend` | ~200 KB | 80-100 files |
| `/infrastructure` | ~20 KB | 15-20 files |
| `/docs` | ~100 KB | 20-25 files |
| `/node_modules` | ~300 MB | 10,000+ files |
| `/venv` | ~50 MB | 1,000+ files |
| **Total (excluding deps)** | ~500 KB | ~150 files |

---

## 🔧 Development Workflow by Directory

### Working on Scraper
```bash
cd scraper/
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/
```

### Working on Frontend
```bash
cd frontend/
npm install
npm run dev
npm test
```

### Deploying Infrastructure
```bash
cd infrastructure/terraform/environments/prod/
terraform init
terraform plan
terraform apply
```

### Running Full Stack Locally
```bash
# From root directory
docker-compose up
```

---

## 🎯 What to Work on by Phase

### Phase 1: Backend (Scraper)
Focus on: `/scraper/src/`, `/scraper/tests/`, `/scraper/lambda/`

### Phase 2: Infrastructure
Focus on: `/infrastructure/terraform/`, `/scripts/setup/`

### Phase 3: Frontend
Focus on: `/frontend/src/`, `/frontend/tests/`

### Phase 4: DevOps
Focus on: `/.github/workflows/`, `/docker/`, `/scripts/deploy/`

---

## ✅ Structure Checklist

When setting up your project, ensure:

- [ ] All directories created with proper structure
- [ ] `__init__.py` files in Python packages
- [ ] `.gitignore` configured for each language/framework
- [ ] Environment variable files (.env) are git-ignored
- [ ] Documentation matches implementation
- [ ] Tests mirror source code structure
- [ ] Configuration files in appropriate locations
- [ ] Scripts have executable permissions

---

## 🔗 Quick Navigation

- **Main Application**: [`/scraper/src/manga_scraper.py`](#scraper-backend-scraping-service)
- **Frontend Entry**: [`/frontend/src/app/page.tsx`](#frontend-nextjs-web-application)
- **Infrastructure**: [`/infrastructure/terraform/main.tf`](#infrastructure-infrastructure-as-code)
- **Documentation**: [`/docs/README.md`](#docs-project-documentation)
- **CI/CD**: [`/.github/workflows/ci.yml`](#github-github-configuration)

---

*This structure follows industry best practices for monorepo organization with clear separation of concerns between backend, frontend, infrastructure, and documentation.*
