# Digital Collections Monitor

Python tool for monitoring availability and performance of digital archives and collections.

## Overview

This tool tracks uptime statistics and response times for major cultural heritage institutions including:
- Library of Congress
- Digital Public Library of America (DPLA)
- Internet Archive
- Academic repositories and digital collections

## Features

- Real-time availability monitoring
- Response time tracking
- 📈Uptime statistics
- 🏛️ Pre-configured for major digital archives
- 📋 Status reporting

## Prerequisites

- Python 3.6 or higher
- `requests` library

## Installation

1. clone this repo:
```bash
git clone https://github.com/danipagano/digital-collections-monitor/tree/main

cd digital-collections-monitor
```

2. install dependencies:
```bash
pip install requests
```

## Usage

### 1. run first test:
```bash
python monitor.py --check
```

### 2. view results:
```bash
python monitor.py --status
```

that's it!
use `--check` to run monitoring tests and `--status` to view the results.

## Sample Output

![Sample Output](https://github.com/user-attachments/assets/4c3d8a0a-f01d-4517-857f-d6f50a162145)

## LICENSE

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


*Built for digital preservation and cultural heritage communities*
