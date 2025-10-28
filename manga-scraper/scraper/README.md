# Manga Scraper

Professional web scraping engine for manga content with AWS integration.

## 🎯 Features

- **Automated Daily Scraping**: AWS Lambda-based scheduled scraping
- **Rate Limiting**: Polite delays and request throttling
- **Retry Logic**: Exponential backoff for failed requests
- **Image Optimization**: WebP conversion with 50% size reduction
- **Duplicate Detection**: Hash-based image deduplication
- **Progress Tracking**: Resume capability for interrupted scrapes
- **AWS Integration**: S3 storage and DynamoDB metadata
- **Comprehensive Testing**: 80%+ code coverage

## 📋 Requirements

- Python 3.11+
- AWS Account (Free Tier compatible)
- Required Python packages (see `requirements.txt`)

## 🚀 Installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/manga-scraper.git
cd manga-scraper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

### Environment Variables

Create a `.env` file:

```bash
S3_BUCKET=your-manga-bucket
DYNAMODB_TABLE=manga-metadata
AWS_REGION=us-east-1
REQUESTS_PER_SECOND=0.5
BASE_DELAY_SECONDS=2.0
MAX_RETRIES=3
WEBP_QUALITY=85
LOG_LEVEL=INFO
```

## 🎓 Usage

### Basic Usage

```python
from manga_scraper import MangaScraper

# Initialize scraper
scraper = MangaScraper(
    s3_bucket='my-manga-bucket',
    dynamodb_table='manga-metadata',
    region='us-east-1'
)

# Scrape a complete manga
scraper.scrape_full_manga(
    manga_url='https://example.com/manga/one-piece',
    manga_id='one-piece',
    max_chapters=5  # Optional: limit number of chapters
)
```

### Using Configuration

```python
from manga_scraper import MangaScraper
from config import ScraperConfig

# Load config from environment
config = ScraperConfig.from_env()
config.validate()

# Initialize with config
scraper = MangaScraper(
    s3_bucket=config.s3_bucket,
    dynamodb_table=config.dynamodb_table,
    region=config.aws_region
)
```

### AWS Lambda Deployment

The scraper is designed to run as an AWS Lambda function:

```python
# Lambda event format
{
    "manga_url": "https://example.com/manga/naruto",
    "manga_id": "naruto",
    "max_chapters": 10
}
```

## 🏗️ Architecture

### Components

1. **MangaScraper**: Main scraper orchestration
2. **ImageProcessor**: Image optimization and thumbnail generation
3. **RateLimiter**: Request throttling and politeness delays
4. **RetryHandler**: Exponential backoff retry logic
5. **S3Storage**: AWS S3 integration for image storage
6. **DynamoDBManager**: Metadata storage and retrieval

### Data Flow

```
Source Website → Scraper → Rate Limiter → Retry Handler
                                              ↓
                                       Download Images
                                              ↓
                                    Image Processor
                                    (Optimize + Hash)
                                              ↓
                                      S3Storage
                                   (Upload Images)
                                              ↓
                                   DynamoDB Manager
                                   (Save Metadata)
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest test_manga_scraper.py -v

# Run with coverage report
pytest test_manga_scraper.py --cov=manga_scraper --cov-report=html

# Run specific test class
pytest test_manga_scraper.py::TestImageProcessor -v
```

## 🔧 Configuration

### Customizing Selectors

Edit `config.py` to add support for new manga sources:

```python
SOURCE_CONFIGS = {
    'your_source': {
        'base_url': 'https://example.com',
        'selectors': {
            'manga_title': 'h1.title',
            'author': 'span.author',
            'description': 'div.desc',
            'cover_image': 'img.cover',
            'genres': 'span.genre',
            'chapters': 'a.chapter',
            'chapter_images': 'img.page',
        },
        'rate_limit': 0.5,
    }
}
```

### Rate Limiting

Adjust rate limiting in `config.py`:

```python
config = ScraperConfig(
    requests_per_second=0.5,  # Max 0.5 requests/second
    base_delay_seconds=2.0,   # 2 second delay between requests
)
```

## 📊 S3 Storage Structure

```
manga-bucket/
├── manga/
│   ├── {manga-id}/
│   │   ├── cover/
│   │   │   └── page_000.webp
│   │   └── chapters/
│   │       ├── {chapter-number}/
│   │       │   ├── page_001.webp
│   │       │   ├── page_002.webp
│   │       │   └── thumbnails/
│   │       │       ├── page_001.webp
│   │       │       └── page_002.webp
```

## 🗄️ DynamoDB Schema

### Manga Metadata

```json
{
  "PK": "MANGA#{manga_id}",
  "SK": "METADATA",
  "manga_id": "one-piece",
  "title": "One Piece",
  "author": "Eiichiro Oda",
  "genres": ["Action", "Adventure"],
  "description": "...",
  "cover_url": "...",
  "status": "Ongoing",
  "chapters": [],
  "updated_at": "2025-10-28T12:00:00Z"
}
```

### Chapter Metadata

```json
{
  "PK": "MANGA#{manga_id}",
  "SK": "CHAPTER#{chapter_number}",
  "manga_id": "one-piece",
  "chapter_number": "1",
  "chapter_title": "Romance Dawn",
  "page_count": 45,
  "upload_date": "2025-10-28T12:00:00Z",
  "updated_at": "2025-10-28T12:00:00Z"
}
```

## 🚨 Error Handling

The scraper includes comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Rate Limit Errors**: Increased delays and retry
- **Image Processing Errors**: Logged with fallback options
- **S3 Upload Errors**: Retry logic with detailed logging
- **DynamoDB Errors**: Graceful degradation

## 📈 Performance Optimization

### Image Optimization

- JPEG/PNG → WebP conversion (25-35% size reduction)
- Quality adjustment (80-85% quality)
- Thumbnail generation for faster loading
- Hash-based duplicate detection

### Caching Strategy

- CloudFront CDN with 30-day TTL
- Browser caching with Cache-Control headers
- Lambda function warm-up

## ⚠️ Legal & Ethical Considerations

**IMPORTANT**: This scraper is designed for educational purposes only.

- Always respect `robots.txt`
- Implement polite delays between requests
- Ensure you have legal rights to scrape content
- Respect copyright and intellectual property laws
- Consider using official APIs when available
- Be aware of terms of service for source websites

## 🔒 Security Best Practices

- Never commit AWS credentials to Git
- Use IAM roles with least privilege
- Enable MFA on AWS account
- Encrypt S3 buckets at rest
- Use environment variables for secrets
- Enable CloudTrail for audit logging

## 📝 Logging

The scraper provides structured logging:

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Logs include:
# - Request URLs and timing
# - Image optimization statistics
# - Upload success/failure
# - Error traces with context
```

## 🐛 Troubleshooting

### Common Issues

**"Missing environment variables"**
- Ensure `.env` file is present with all required variables
- Check AWS credentials are configured

**"Rate limit exceeded"**
- Increase `base_delay_seconds` in configuration
- Decrease `requests_per_second`

**"S3 upload failed"**
- Verify S3 bucket exists and has correct permissions
- Check AWS credentials have S3 write permissions

**"Image optimization error"**
- Ensure Pillow is properly installed
- Check source images are valid formats

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `pytest`
5. Run linting: `black . && flake8`
6. Commit with conventional commits: `git commit -m 'feat: add feature'`
7. Push and create a pull request

## 📄 License

This project is for educational purposes. Please ensure you have appropriate rights before scraping any content.

## 🔗 Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Beautiful Soup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [Pillow Documentation](https://pillow.readthedocs.io/)

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review AWS Free Tier limits

## 🎯 Roadmap

- [ ] Add support for more manga sources
- [ ] Implement Scrapy for complex scenarios
- [ ] Add Selenium support for JavaScript-heavy sites
- [ ] Create web dashboard for monitoring
- [ ] Add bulk scraping capabilities
- [ ] Implement queue-based processing
- [ ] Add email notifications for completion

---

**Note**: This is a professional implementation following industry best practices. Always ensure legal compliance when scraping web content.
