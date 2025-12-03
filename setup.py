"""
PhoneTracker CLI Setup

Install with: pip install -e .
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='phonetracker',
    version='1.0.0',
    author='Your Name',
    author_email='your.email@example.com',
    description='CLI tool to track phone locations via VoIP calls',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/kbornfas/Phone-locator',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Communications :: Telephony',
        'Topic :: Utilities',
    ],
    python_requires='>=3.8',
    install_requires=[
        'click>=8.1.7',
        'rich>=13.7.0',
        'twilio>=8.11.0',
        'requests>=2.31.0',
        'python-dotenv>=1.0.0',
        'pyyaml>=6.0.1',
        'sqlalchemy>=2.0.23',
        'cryptography>=41.0.7',
        'phonenumbers>=8.13.26',
    ],
    entry_points={
        'console_scripts': [
            'phonetracker=cli.main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
