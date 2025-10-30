# AWS Manga Library - Complete Deployment Guide

Welcome! This guide will walk you through deploying the Manga Scraper application on AWS from scratch. No prior AWS or coding knowledge required - just follow the steps carefully!

---

## Table of Contents

1. [What You're Building](#what-youre-building)
2. [Prerequisites](#prerequisites)
3. [Part 1: Setting Up Your Computer](#part-1-setting-up-your-computer)
4. [Part 2: Setting Up Your AWS Account](#part-2-setting-up-your-aws-account)
5. [Part 3: Creating AWS Resources](#part-3-creating-aws-resources)
6. [Part 4: Initializing the Database](#part-4-initializing-the-database)
7. [Part 5: Deploying the Lambda Function](#part-5-deploying-the-lambda-function)
8. [Part 6: Testing Your Deployment](#part-6-testing-your-deployment)
9. [Part 7: Monitoring and Viewing Logs](#part-7-monitoring-and-viewing-logs)
10. [Troubleshooting](#troubleshooting)
11. [Understanding Your AWS Resources](#understanding-your-aws-resources)
12. [Cost Management](#cost-management)
13. [Deploying to Multiple Environments](#deploying-to-multiple-environments)

---

## SPECIAL

```bash
git fetch origin
git reset --hard origin/main
```

```bash
wsl -d Ubuntu
```

## What You're Building

You're deploying a **serverless manga scraper application** on AWS that can:
- Scrape manga from websites like MangaDex and MangaKakalot
- Store manga images in the cloud (Amazon S3)
- Save manga information in a database (Amazon DynamoDB)
- Process and optimize images automatically
- Run without managing any servers (AWS Lambda)

**AWS Services Used:**
- **AWS Lambda** - Runs your code without servers
- **Amazon S3** - Stores manga images
- **Amazon DynamoDB** - Stores manga information (title, chapters, etc.)
- **IAM** - Manages security and permissions
- **CloudWatch** - Monitors your application and logs

---

## Prerequisites

Before you begin, you'll need:

1. **An AWS Account** (we'll create this in Part 2)
2. **A Computer** running:
   - **Windows**: Windows 10/11 with WSL (Windows Subsystem for Linux) installed, OR
   - **Mac**: macOS 10.14 or later, OR
   - **Linux**: Ubuntu 18.04 or later (or similar)
3. **About 1 hour** of your time
4. **A credit/debit card** for AWS (required even for free tier)

> **Note on Costs**: AWS offers a free tier that covers most of this deployment. You'll likely pay $0-5/month for light usage. See [Cost Management](#cost-management) for details.

---

## Part 1: Setting Up Your Computer

### Step 1.1: Install Required Software

You need to install several tools on your computer. Follow the instructions for your operating system.

#### For Windows Users

**Option A: Using WSL (Recommended)**

1. **Install WSL (Windows Subsystem for Linux)**
   - Open PowerShell as Administrator
   - Run: `wsl --install`
   - Restart your computer
   - Ubuntu will open automatically after restart
   - Create a username and password when prompted

2. **Open Ubuntu (WSL)** for all following commands

**Option B: Using Git Bash**
   - Download and install Git Bash from: https://git-scm.com/download/win

#### For Mac Users

1. **Open Terminal** (Applications → Utilities → Terminal)
   - You'll use Terminal for all commands

#### For Linux Users

1. **Open Terminal**
   - You already have everything you need!

---

### Step 1.2: Install AWS CLI

The AWS CLI lets you control AWS from your computer.

**For Mac/Linux/WSL:**

```bash
# Download the AWS CLI installer
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

# Unzip it
unzip awscliv2.zip

# Install it
sudo ./aws/install

# Verify installation
aws --version
```

You should see something like: `aws-cli/2.x.x Python/3.x.x Linux/x.x.x`

**For Windows (without WSL):**
- Download the installer from: https://awscli.amazonaws.com/AWSCLIV2.msi
- Run the installer
- Open a new Command Prompt
- Type: `aws --version`

> **Troubleshooting**: If `aws --version` doesn't work, close and reopen your terminal.

---

### Step 1.3: Install Python 3

Python is the programming language this application uses.

**Check if you already have Python:**
```bash
python3 --version
```

If you see `Python 3.9` or higher, you're good! Skip to Step 1.4.

**Install Python:**

- **Mac**:
  ```bash
  # Install Homebrew first (if you don't have it)
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  # Install Python
  brew install python@3.11
  ```

- **Ubuntu/WSL**:
  ```bash
  sudo apt update
  sudo apt install python3 python3-pip -y
  ```

- **Windows (without WSL)**:
  - Download from: https://www.python.org/downloads/
  - Run installer
  - **Important**: Check "Add Python to PATH" during installation

**Verify Python installation:**
```bash
python3 --version
pip3 --version
```

---

### Step 1.4: Install Additional Tools

**For Mac/Linux/WSL:**

```bash
# zip utility (usually already installed)
sudo apt install zip -y  # Ubuntu/WSL

# For Mac
brew install zip  # Usually not needed, already installed
```

**For Windows:**
- `zip` is included with Git Bash or WSL

---

### Step 1.5: Get the Code

Download the project code to your computer.

```bash
# Navigate to your desired folder (example: Documents)
cd ~/Documents

# Clone the repository
git clone <your-repo-url> aws-manga-library
cd aws-manga-library

# Verify you have the correct structure
ls -la
```

You should see folders like: `manga-scraper/`, `scripts/`, etc.

**Don't have the repo URL yet?**
If this is your own code, you already have it. If you're following a tutorial, replace `<your-repo-url>` with the actual URL.

---

## Part 2: Setting Up Your AWS Account

### Step 2.1: Create an AWS Account

If you don't have an AWS account:

1. Go to: https://aws.amazon.com
2. Click **"Create an AWS Account"**
3. Fill in:
   - Email address
   - Password
   - AWS account name (can be anything)
4. Choose **"Personal"** account type
5. Enter your payment information (required, even for free tier)
6. Verify your phone number
7. Choose **"Basic Support - Free"**
8. Complete sign-up

> **Important**: You won't be charged unless you exceed the free tier limits. See [Cost Management](#cost-management).

---

### Step 2.2: Create an IAM User (for security)

**Why?** It's a security best practice to create a separate user instead of using your root account.

1. **Sign in to AWS Console**: https://console.aws.amazon.com
2. In the search bar at the top, type **"IAM"** and click on it
3. In the left sidebar, click **"Users"**
4. Click **"Create user"**
5. **User name**: `manga-scraper-admin`
6. Click **"Next"**
7. **Set permissions**:
   - Select **"Attach policies directly"**
   - Search for and check: **"AdministratorAccess"**
8. Click **"Next"**, then **"Create user"**

> **Note**: AdministratorAccess is powerful. For production, use more restricted permissions.

---

### Step 2.3: Create Access Keys

Access keys let your computer talk to AWS.

1. In the IAM Users page, click on **"manga-scraper-admin"**
2. Click the **"Security credentials"** tab
3. Scroll down to **"Access keys"**
4. Click **"Create access key"**
5. Select **"Command Line Interface (CLI)"**
6. Check the checkbox at the bottom
7. Click **"Next"**
8. (Optional) Add a description: "Manga Scraper Deployment"
9. Click **"Create access key"**

**IMPORTANT**: You'll see:
- **Access key ID** (like: AKIAIOSFODNN7EXAMPLE)
- **Secret access key** (like: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY)

**Copy both of these** - you'll need them in the next step!

> **Security Warning**: Never share these keys or commit them to GitHub. Treat them like passwords.

---

### Step 2.4: Configure AWS CLI

Tell the AWS CLI to use your access keys.

```bash
aws configure
```

It will ask for:

```
AWS Access Key ID [None]: <paste your access key ID>
AWS Secret Access Key [None]: <paste your secret access key>
Default region name [None]: eu-west-3
Default output format [None]: json
```

**Region options**:
- `eu-west-3` (Virginia - most services available)
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `ap-southeast-1` (Singapore)

**Verify it works:**
```bash
aws sts get-caller-identity
```

You should see JSON output with your AWS account ID and user ARN. Success!

---

## Part 3: Creating AWS Resources

Now we'll create all the AWS infrastructure your application needs!

### Step 3.1: Navigate to Scripts Directory

```bash
# From the aws-manga-library folder
cd manga-scraper

# Check that the setup script exists
ls -la scripts/setup/create-aws-resources.sh
```

You should see the file listed.

---

### Step 3.2: Make Scripts Executable

```bash
# Make all scripts executable
chmod +x scripts/setup/*.sh
chmod +x scripts/deploy/*.sh
```

---

### Step 3.3: Run the Setup Script

This script creates:
- 2 S3 buckets (for images and backups)
- 1 DynamoDB table (for manga information)
- 1 IAM role (for Lambda permissions)
- Configuration file (.env.dev)

```bash
./scripts/setup/create-aws-resources.sh dev
```

**What's `dev`?**
This is your "environment" - it helps separate development from production. Resources will be named like `manga-scraper-dev-images`.

**The script will:**
1. ✓ Check prerequisites (AWS CLI, credentials)
2. ✓ Create S3 bucket for images
3. ✓ Create S3 bucket for backups
4. ✓ Create DynamoDB table
5. ✓ Create IAM role with permissions
6. ✓ Generate .env.dev configuration file

**This takes about 2-3 minutes.**

### Step 3.4: Verify Resources Created

```bash
# Check if S3 buckets exist
aws s3 ls | grep manga-scraper-dev

# Check DynamoDB table
aws dynamodb list-tables | grep manga-scraper-dev

# Check IAM role
aws iam get-role --role-name manga-scraper-dev-lambda-role
```

You should see your resources listed!

### Step 3.5: Review Configuration File

```bash
cat .env.dev
```

You'll see something like:
```bash
AWS_REGION=eu-west-3
AWS_ACCOUNT_ID=123456789012
S3_BUCKET=manga-scraper-dev-images
S3_BACKUP_BUCKET=manga-scraper-dev-backups
DYNAMODB_TABLE=manga-scraper-dev-metadata
LAMBDA_ROLE_ARN=arn:aws:iam::123456789012:role/manga-scraper-dev-lambda-role
LAMBDA_FUNCTION=manga-scraper-dev
# ... more settings
```

This file contains all the configuration your application needs!

---

## Part 4: Initializing the Database

Now we'll set up the DynamoDB database with initial data.

### Step 4.1: Run Database Initialization Script

```bash
./scripts/setup/init-database.sh dev
```

**This script will:**
1. ✓ Verify DynamoDB table exists
2. ✓ Create system configuration
3. ✓ Initialize statistics tracking
4. ✓ Create manga sources (MangaDex, MangaKakalot)
5. ✓ Create 10 manga categories (Action, Adventure, Comedy, etc.)
6. ✓ Initialize job queue metadata
7. ✓ Create documentation file

**This takes about 30 seconds.**

### Step 4.2: Verify Database Items

```bash
# Count items in the table
aws dynamodb scan \
  --table-name manga-scraper-dev-metadata \
  --select "COUNT" \
  --region eu-west-3
```

You should see about 14-15 items created.

### Step 4.3: View Database Documentation

```bash
cat docs/database-schema.md
```

This file explains how data is structured in DynamoDB.

---

## Part 5: Deploying the Lambda Function

Time to deploy the actual application code to AWS Lambda!

### Step 5.1: Check Python Dependencies

Verify the requirements file exists:

```bash
cd scraper

# Check requirements file exists
cat lambda/requirements.txt
```

You should see packages like: `requests`, `beautifulsoup4`, `Pillow`, `boto3`, etc.

### Step 5.2: Run Deployment Script

```bash
# Go back to the manga-scraper directory
cd ..

# Run the deployment
./scripts/deploy/deploy-lambda.sh dev
```

**This script will:**
1. ✓ Load environment variables from .env.dev
2. ✓ Check prerequisites (AWS CLI, Python, zip)
3. ✓ Create temporary package directory
4. ✓ Install Python dependencies with Lambda-compatible platform flags
5. ✓ Copy source code
6. ✓ Optimize package size (remove tests, cache files)
7. ✓ Create zip archive (deployment package)
8. ✓ Upload to AWS Lambda (create or update function)
9. ✓ Configure environment variables
10. ✓ Set memory (1024 MB) and timeout (300 seconds)
11. ✓ Wait for function to be ready
12. ✓ Clean up temporary files

**This takes about 2-5 minutes** (depending on your internet speed).

**How it works:**
The script uses pip with special flags (`--platform manylinux2014_x86_64 --python-version 3.11`) to ensure all binary dependencies (like Pillow for image processing) are compiled for AWS Lambda's Amazon Linux 2 environment, not your local system.

### Step 5.3: Verify Lambda Function

```bash
# Check Lambda function exists
aws lambda get-function --function-name manga-scraper-dev --region eu-west-3
```

You'll see detailed information about your function including:
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 300 seconds
- **Code Size**: ~15-20 MB

**Success!** Your Lambda function is now deployed!

---

## Part 6: Testing Your Deployment

Let's make sure everything works!

### Step 6.1: Test with Health Check

First, do a simple health check:

```bash
aws lambda invoke \
  --function-name manga-scraper-dev \
  --region eu-west-3 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action":"health_check"}' \
  response.json

# View the response
cat response.json
```

**Expected output:**
```json
{
  "statusCode": 200,
  "body": {
    "success": true,
    "message": "Manga scraper is healthy",
    "version": "1.0.0"
  }
}
```

✓ **If you see this, your Lambda function is working!**

---

### Step 6.2: Test Scraping a Manga (Simulation)

> **Important Note**: Actually scraping manga from websites requires careful consideration of:
> - Website terms of service
> - Rate limiting
> - Legal permissions
>
> For testing purposes, we'll use a dry-run or test the infrastructure only.

**Test the infrastructure with a test payload:**

```bash
aws lambda invoke \
  --function-name manga-scraper-dev \
  --region eu-west-3 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action":"list_manga","source":"mangadex","limit":5}' \
  response.json

cat response.json
```

---

### Step 6.3: View CloudWatch Logs

```bash
# View recent logs
aws logs tail /aws/lambda/manga-scraper-dev --follow --region eu-west-3
```

**What you'll see:**
- `START RequestId: ...` - Function started
- Log messages from your code
- `END RequestId: ...` - Function finished
- `REPORT RequestId: ...` - Performance metrics (duration, memory used)

Press `Ctrl+C` to stop viewing logs.

---

## Part 7: Monitoring and Viewing Logs

### Step 7.1: View Logs in AWS Console

For a more user-friendly experience:

1. Go to: https://console.aws.amazon.com
2. Search for **"CloudWatch"** in the top search bar
3. In the left sidebar, click **"Logs" → "Log groups"**
4. Find and click: `/aws/lambda/manga-scraper-dev`
5. Click on the latest **"Log stream"**
6. View your logs in real-time!

---

### Step 7.2: View S3 Bucket Contents

Check what's stored in S3:

```bash
# List files in images bucket
aws s3 ls s3://manga-scraper-dev-images/ --recursive --human-readable
```

Initially, it will be empty. After scraping manga, you'll see files like:
```
manga/one-piece/chapters/1/page_001.webp
manga/one-piece/chapters/1/page_002.webp
```

---

### Step 7.3: View DynamoDB Data

**Using AWS CLI:**
```bash
# Scan the table (get all items)
aws dynamodb scan \
  --table-name manga-scraper-dev-metadata \
  --region eu-west-3 \
  --max-items 10
```

**Using AWS Console:**
1. Go to: https://console.aws.amazon.com
2. Search for **"DynamoDB"**
3. Click **"Tables"** in left sidebar
4. Click **"manga-scraper-dev-metadata"**
5. Click **"Explore table items"**
6. View your data!

---

## Troubleshooting

### Problem: "aws: command not found"

**Solution:**
- Reinstall AWS CLI (Step 1.2)
- Close and reopen your terminal
- On Mac, try: `sudo /usr/local/bin/python3 -m pip install awscli --upgrade`

---

### Problem: "The security token included in the request is invalid"

**Solution:**
Your AWS credentials are incorrect or expired.
```bash
# Reconfigure AWS CLI
aws configure

# Verify credentials
aws sts get-caller-identity
```

---

### Problem: "An error occurred (AccessDenied) when calling..."

**Solution:**
Your IAM user doesn't have sufficient permissions.
1. Go to AWS Console → IAM → Users
2. Click your user
3. Ensure **"AdministratorAccess"** policy is attached

---

### Problem: Script shows "Permission denied"

**Solution:**
```bash
# Make scripts executable
chmod +x scripts/setup/*.sh
chmod +x scripts/deploy/*.sh
```

---

### Problem: "Role arn:aws:iam::xxx:role/xxx is invalid or cannot be assumed"

**Solution:**
Wait 10 seconds for IAM role to propagate, then retry:
```bash
sleep 10
./scripts/deploy/deploy-lambda.sh dev
```

---

### Problem: Lambda function timeout

**Solution:**
Increase timeout:
```bash
aws lambda update-function-configuration \
  --function-name manga-scraper-dev \
  --timeout 600 \
  --region eu-west-3
```

---

### Problem: "No module named 'requests'" in Lambda

**Solution:**
Dependencies weren't packaged correctly. Redeploy:
```bash
./scripts/deploy/deploy-lambda.sh dev
```

---

### Problem: "cannot import name '_imaging' from 'PIL'" in Lambda

**Solution:**
This means Pillow was built for the wrong architecture. This happens when you install dependencies with regular `pip install` instead of using Lambda-compatible platform flags.

**The Fix:**
The deployment script (`./scripts/deploy/deploy-lambda.sh`) has been updated to automatically use Lambda-compatible flags. Simply redeploy:

```bash
# Navigate to the manga-scraper directory
cd ~/projects/aws-manga-library/manga-scraper

# Pull latest changes if you haven't already
git pull

# Redeploy using the fixed script
./scripts/deploy/deploy-lambda.sh dev
```

The script now uses:
```bash
pip install --platform manylinux2014_x86_64 --python-version 3.11 --only-binary=:all:
```

This ensures Pillow and other binary packages are compiled for AWS Lambda's environment.

**Verify the deployment:**
```bash
# Test the Lambda function
aws lambda invoke \
  --function-name manga-scraper-dev \
  --region eu-west-3 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action":"health_check"}' \
  response.json

# Check the response
cat response.json
```

You should see:
```json
{
  "statusCode": 200,
  "body": "{\"success\": true, \"message\": \"Manga scraper is healthy\", \"version\": \"1.0.0\"}"
}
```

**If you still get errors**, check the CloudWatch logs:
```bash
aws logs tail /aws/lambda/manga-scraper-dev --follow --region eu-west-3
```

---

## Understanding Your AWS Resources

### What Did We Create?

| Resource | Name | Purpose | Cost |
|----------|------|---------|------|
| **S3 Bucket** | `manga-scraper-dev-images` | Stores manga images | $0.023/GB/month |
| **S3 Bucket** | `manga-scraper-dev-backups` | Stores backups | Glacier: $0.004/GB/month |
| **DynamoDB Table** | `manga-scraper-dev-metadata` | Stores manga info | First 25 GB free |
| **Lambda Function** | `manga-scraper-dev` | Runs scraper code | First 1M requests/month free |
| **IAM Role** | `manga-scraper-dev-lambda-role` | Permissions for Lambda | Free |
| **CloudWatch Logs** | `/aws/lambda/manga-scraper-dev` | Application logs | First 5 GB free |

---

### How Do They Work Together?

```
┌─────────────────┐
│  You Send a     │
│  Request        │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  AWS Lambda                     │
│  (manga-scraper-dev)            │
│                                 │
│  1. Receives request            │
│  2. Scrapes manga website       │
│  3. Downloads images            │
│  4. Optimizes images            │
└─────┬─────────────────────┬─────┘
      │                     │
      │                     │
      ▼                     ▼
┌──────────────┐    ┌──────────────────┐
│  S3 Bucket   │    │  DynamoDB Table  │
│  (Images)    │    │  (Metadata)      │
│              │    │                  │
│  Stores:     │    │  Stores:         │
│  - Manga     │    │  - Titles        │
│    images    │    │  - Authors       │
│  - Chapters  │    │  - Chapters      │
│  - Pages     │    │  - Statistics    │
└──────────────┘    └──────────────────┘
```

---

### IAM Role Permissions Explained

The `manga-scraper-dev-lambda-role` allows Lambda to:

1. **S3 Permissions**:
   - `s3:PutObject` - Upload images
   - `s3:GetObject` - Download images
   - `s3:DeleteObject` - Delete images
   - `s3:ListBucket` - List files

2. **DynamoDB Permissions**:
   - `dynamodb:PutItem` - Add manga data
   - `dynamodb:GetItem` - Read manga data
   - `dynamodb:Query` - Search for manga
   - `dynamodb:Scan` - List all manga

3. **CloudWatch Permissions**:
   - `logs:CreateLogGroup` - Create log groups
   - `logs:PutLogEvents` - Write logs

**This follows the "Principle of Least Privilege"** - Lambda only has the permissions it needs.

---

## Cost Management

### Free Tier Limits (First 12 Months)

- **Lambda**: 1 million requests/month + 400,000 GB-seconds compute
- **S3**: 5 GB storage + 20,000 GET requests + 2,000 PUT requests
- **DynamoDB**: 25 GB storage + 25 read/write capacity units
- **CloudWatch Logs**: 5 GB ingestion + 5 GB storage

### Estimated Monthly Costs

**Light Usage** (1-2 manga/day, ~100 chapters):
- S3 Storage: ~$0.10
- Lambda Executions: Free
- DynamoDB: Free
- **Total: ~$0.10-0.50/month**

**Moderate Usage** (10 manga/day, ~500 chapters):
- S3 Storage (10 GB): ~$0.23
- Lambda Executions: Free
- DynamoDB: Free
- **Total: ~$1-3/month**

**Heavy Usage** (50+ manga/day, 2000+ chapters):
- S3 Storage (50 GB): ~$1.15
- Lambda Executions: ~$0.50
- DynamoDB: Free (or $0.50 if over 25 GB)
- **Total: ~$2-5/month**

### Tips to Minimize Costs

1. **Enable S3 Lifecycle Policies** (already configured):
   - Transitions old images to cheaper storage
   - Deletes old backups after 90 days

2. **Use DynamoDB On-Demand Pricing**:
   - Only pay for what you use
   - No minimum fees

3. **Monitor Usage**:
   ```bash
   # Check S3 bucket size
   aws s3 ls s3://manga-scraper-dev-images --recursive --summarize --human-readable

   # Check Lambda invocations (in console)
   # Go to CloudWatch → Metrics → Lambda
   ```

4. **Set Billing Alerts**:
   - Go to AWS Console → Billing
   - Set up alerts for $5, $10, $20 thresholds

5. **Delete Test Resources**:
   ```bash
   # Delete old test files
   aws s3 rm s3://manga-scraper-dev-images/test/ --recursive
   ```

---

## Deploying to Multiple Environments

### Understanding Environments

- **dev** (Development): For testing and development
- **staging**: For final testing before production
- **prod** (Production): For real use

Each environment has completely separate resources!

---

### Deploy to Staging

```bash
# Create staging resources
./scripts/setup/create-aws-resources.sh staging

# Initialize staging database
./scripts/setup/init-database.sh staging

# Deploy to staging
./scripts/deploy/deploy-lambda.sh staging
```

Your resources will be named:
- `manga-scraper-staging-images`
- `manga-scraper-staging-metadata`
- `manga-scraper-staging` (Lambda)

---

### Deploy to Production

**Important**: Only do this when you've tested everything in dev/staging!

```bash
# Create production resources
./scripts/setup/create-aws-resources.sh prod

# Initialize production database
./scripts/setup/init-database.sh prod

# Deploy to production
./scripts/deploy/deploy-lambda.sh prod
```

**Production Differences**:
- Lambda creates versioned aliases
- More conservative rate limits recommended
- Should set up monitoring alarms
- Consider enabling AWS CloudFront CDN

---

## Advanced: Cleaning Up Resources

If you want to delete everything (be careful!):

### Delete Lambda Function
```bash
aws lambda delete-function --function-name manga-scraper-dev --region eu-west-3
```

### Delete S3 Buckets
```bash
# Empty buckets first (required)
aws s3 rm s3://manga-scraper-dev-images --recursive
aws s3 rm s3://manga-scraper-dev-backups --recursive

# Delete buckets
aws s3 rb s3://manga-scraper-dev-images
aws s3 rb s3://manga-scraper-dev-backups
```

### Delete DynamoDB Table
```bash
aws dynamodb delete-table --table-name manga-scraper-dev-metadata --region eu-west-3
```

### Delete IAM Role
```bash
# Delete role policy first
aws iam delete-role-policy \
  --role-name manga-scraper-dev-lambda-role \
  --policy-name manga-scraper-dev-lambda-policy

# Delete role
aws iam delete-role --role-name manga-scraper-dev-lambda-role
```

---

## Next Steps

Congratulations! You've successfully deployed the Manga Scraper to AWS!

### What You Can Do Now:

1. **Scrape Your First Manga**:
   - Modify the Lambda function to scrape a specific manga
   - Use the test payload in Step 6.2

2. **Build a Frontend**:
   - Create a web interface to trigger scraping
   - Display manga from your DynamoDB table
   - Show images from S3

3. **Schedule Automatic Scraping**:
   - Use AWS EventBridge to run Lambda on a schedule
   - Scrape new chapters automatically

4. **Add More Features**:
   - Image optimization improvements
   - Duplicate detection
   - Notification system (SNS)
   - Search functionality

5. **Set Up CI/CD**:
   - Use GitHub Actions to auto-deploy on push
   - Automated testing before deployment

---

## Getting Help

### Documentation Links

- **AWS Lambda**: https://docs.aws.amazon.com/lambda/
- **Amazon S3**: https://docs.aws.amazon.com/s3/
- **DynamoDB**: https://docs.aws.amazon.com/dynamodb/
- **AWS CLI**: https://docs.aws.amazon.com/cli/

### Common Commands Reference

```bash
# View Lambda logs
aws logs tail /aws/lambda/manga-scraper-dev --follow

# List S3 files
aws s3 ls s3://manga-scraper-dev-images --recursive

# Scan DynamoDB table
aws dynamodb scan --table-name manga-scraper-dev-metadata

# Invoke Lambda function
aws lambda invoke --function-name manga-scraper-dev \
  --cli-binary-format raw-in-base64-out \
  --payload '{"action":"health_check"}' response.json

# Update Lambda function
./scripts/deploy/deploy-lambda.sh dev

# View environment config
cat .env.dev
```

---

## Conclusion

You've successfully:
- ✅ Set up your computer with AWS CLI and Python
- ✅ Created an AWS account and configured credentials
- ✅ Deployed S3 buckets, DynamoDB table, IAM role, and Lambda function
- ✅ Initialized your database with seed data
- ✅ Tested your deployment
- ✅ Learned how to monitor and troubleshoot

**Your manga scraper is now running on AWS!**

Remember:
- Always test in `dev` environment first
- Monitor your costs regularly
- Keep your AWS credentials secure
- Follow website terms of service when scraping

Happy scraping! 🎉

---

**Last Updated**: 2025-01-29
**Version**: 1.0.0
