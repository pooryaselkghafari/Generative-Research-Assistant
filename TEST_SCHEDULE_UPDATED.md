# Complete Test Schedule - Updated

## 📋 Complete Test Schedule Table

| Category | Interval | Time | Day | Target Score | Priority | Status |
|----------|----------|------|-----|--------------|----------|--------|
| **Security** | Daily | 02:00 | - | 95% | 🔴 HIGH | ✅ Active |
| **Database** | Daily | 03:00 | - | 85% | 🔴 HIGH | ✅ Active |
| **Performance** | Daily | 04:00 | - | 80% | 🟡 MEDIUM | ✅ Active |
| **Unit** | On Commit | - | - | 80% | 🔴 HIGH | ✅ Active |
| **Integration** | Daily | 05:00 | - | 75% | 🟡 MEDIUM | ✅ Active |
| **API** | Daily | 06:00 | - | 80% | 🟡 MEDIUM | ✅ Active |
| **E2E** | Weekly | 02:00 | Sunday | 70% | 🟢 LOW | ✅ Active |
| **Static Analysis** | On Commit | - | - | 80% | 🔴 HIGH | ✅ Active |
| **Dependency Scan** | Weekly | 03:00 | Sunday | 95% | 🔴 HIGH | ✅ Active |
| **Coverage** | On Commit | - | - | 80% | 🔴 HIGH | ✅ Active |
| **Backup** | Weekly | 04:00 | Sunday | 85% | 🔴 HIGH | ✅ Active |
| **Monitoring** | Daily | 07:00 | - | 85% | 🔴 HIGH | ✅ Active |
| **Cron** | Daily | 08:00 | - | 80% | 🟡 MEDIUM | ✅ Active |
| **Frontend** | On Commit | - | - | 75% | 🟡 MEDIUM | ✅ Active |

---

## 🚀 Execution Commands

### Run All Tests
```bash
python manage.py test_runner all
```

### Run Specific Categories
```bash
python manage.py test_runner security database static_analysis
python manage.py test_runner dependency_scan coverage
```

### Run On-Commit Tests
```bash
python manage.py test_runner unit static_analysis coverage frontend
```

### Run Weekly Tests
```bash
python manage.py test_runner e2e dependency_scan backup
```

### View Latest Results
```bash
python manage.py test_runner --report
```

---

## ⏰ Automated Scheduling (Cron Jobs)

### Daily Tests
```bash
# Security - Daily at 2 AM
0 2 * * * cd /path/to/GRA && python3 manage.py test_runner security

# Database - Daily at 3 AM
0 3 * * * cd /path/to/GRA && python3 manage.py test_runner database

# Performance - Daily at 4 AM
0 4 * * * cd /path/to/GRA && python3 manage.py test_runner performance

# Integration - Daily at 5 AM
0 5 * * * cd /path/to/GRA && python3 manage.py test_runner integration

# API - Daily at 6 AM
0 6 * * * cd /path/to/GRA && python3 manage.py test_runner api

# Monitoring - Daily at 7 AM
0 7 * * * cd /path/to/GRA && python3 manage.py test_runner monitoring

# Cron - Daily at 8 AM
0 8 * * * cd /path/to/GRA && python3 manage.py test_runner cron
```

### Weekly Tests
```bash
# E2E - Weekly on Sunday at 2 AM
0 2 * * 0 cd /path/to/GRA && python3 manage.py test_runner e2e

# Dependency Scan - Weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/GRA && python3 manage.py test_runner dependency_scan

# Backup - Weekly on Sunday at 4 AM
0 4 * * 0 cd /path/to/GRA && python3 manage.py test_runner backup
```

### Pre-Commit Hook
Create `.git/hooks/pre-commit`:
```bash
#!/bin/sh
cd /path/to/GRA
python manage.py test_runner unit static_analysis coverage frontend
if [ $? -ne 0 ]; then
    echo "❌ Pre-commit tests failed. Commit aborted."
    exit 1
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📊 Test Categories Overview

### High Priority Tests (Run Daily/On Commit)
- **Security** (Daily @ 02:00) - Authentication, authorization, data isolation
- **Database** (Daily @ 03:00) - Query performance, integrity, constraints
- **Unit** (On Commit) - Service layer, helper functions
- **Static Analysis** (On Commit) - Code quality, syntax, security patterns
- **Dependency Scan** (Weekly @ 03:00) - Vulnerability scanning
- **Coverage** (On Commit) - Code coverage percentage
- **Backup** (Weekly @ 04:00) - Backup/restore functionality
- **Monitoring** (Daily @ 07:00) - Logging and monitoring

### Medium Priority Tests
- **Performance** (Daily @ 04:00) - Response times, query efficiency
- **Integration** (Daily @ 05:00) - Complete workflows
- **API** (Daily @ 06:00) - API endpoints
- **Cron** (Daily @ 08:00) - Scheduled tasks
- **Frontend** (On Commit) - Templates, static files, JavaScript

### Low Priority Tests
- **E2E** (Weekly @ 02:00) - End-to-end user flows

---

## 📈 Target Scores

| Priority | Target Range | Categories |
|----------|--------------|------------|
| 🔴 HIGH | 85-95% | Security, Database, Dependency Scan, Backup, Monitoring |
| 🟡 MEDIUM | 75-80% | Performance, Integration, API, Cron, Frontend |
| 🟢 LOW | 70% | E2E |

---

**Last Updated**: November 14, 2025
**Total Test Categories**: 14
**Total Tests**: 50+ individual tests



