"""
Setup configuration for manga scraper package
"""

from setuptools import setup, find_packages
import os

# Read README for long description
def read_file(filename):
    """Read file contents"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    return ''

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name='manga-scraper',
    version='1.0.0',
    description='Professional manga scraping service with AWS integration',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/manga-scraper',
    license='MIT',

    # Package configuration
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    python_requires='>=3.9',

    # Dependencies
    install_requires=read_requirements('requirements.txt'),
    extras_require={
        'dev': read_requirements('requirements-dev.txt'),
        'lambda': [
            'requests>=2.31.0',
            'beautifulsoup4>=4.12.2',
            'lxml>=4.9.3',
            'Pillow>=10.1.0',
            'boto3>=1.29.7',
            'python-dateutil>=2.8.2',
        ],
    },

    # Entry points
    entry_points={
        'console_scripts': [
            'manga-scraper=manga_scraper:main',
        ],
    },

    # Metadata
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='manga scraper aws lambda s3 dynamodb web-scraping',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/manga-scraper/issues',
        'Source': 'https://github.com/yourusername/manga-scraper',
        'Documentation': 'https://manga-scraper.readthedocs.io/',
    },

    # Include additional files
    include_package_data=True,
    zip_safe=False,
)
