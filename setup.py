#!/usr/bin/env python3

from setuptools import setup
import re

# Read version from main.py
with open('main.py', 'r') as f:
    version = re.search(r'__version__ = [\'"]([^\'"]*)[\'"]', f.read()).group(1)

# Read long description from README
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='audiobook-creator',
    version=version,
    author='Paying4464',
    author_email='',
    description='Combine audio files into an m4b audiobook with proper indexing',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/Paying4464/audiobook-creator',
    py_modules=['main'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Multimedia :: Sound/Audio :: Conversion',
        'Topic :: Utilities',
    ],
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'audiobook-creator=main:main',
        ],
    },
    keywords='audiobook m4b audio conversion ffmpeg bookplayer',
    project_urls={
        'Bug Reports': 'https://github.com/Paying4464/audiobook-creator/issues',
        'Source': 'https://github.com/Paying4464/audiobook-creator',
    },
)