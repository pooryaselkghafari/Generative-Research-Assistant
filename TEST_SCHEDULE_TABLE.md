# Test Schedule & Results Table

## 📋 Complete Test Schedule

| Category | Interval | Time | Day | Target Score | Priority | Current Score | Status | When to Run |
|----------|----------|------|-----|--------------|----------|----------------|--------|-------------|
| **Security** | Daily | 02:00 | - | **95%** | 🔴 HIGH | **100.0%** | ✅ PASS | Every day at 2 AM |
| **Database** | Daily | 03:00 | - | **85%** | 🔴 HIGH | **100.0%** | ✅ PASS | Every day at 3 AM |
| **Performance** | Daily | 04:00 | - | **80%** | 🟡 MEDIUM | **100.0%** | ✅ PASS | Every day at 4 AM |
| **Unit** | On Commit | - | - | **80%** | 🔴 HIGH | **100.0%** | ✅ PASS | Before every git commit |
| **Integration** | Daily | 05:00 | - | **75%** | 🟡 MEDIUM | **100.0%** | ✅ PASS | Every day at 5 AM |
| **API** | Daily | 06:00 | - | **80%** | 🟡 MEDIUM | **100.0%** | ✅ PASS | Every day at 6 AM |
| **E2E** | Weekly | 02:00 | Sunday | **70%** | 🟢 LOW | **100.0%** | ✅ PASS | Every Sunday at 2 AM |
| **Static Analysis** | On Commit | - | - | **80%** | 🔴 HIGH | **60.0%** | ❌ FAIL | Before every git commit |
| **Dependency Scan** | Weekly | 03:00 | Sunday | **95%** | 🔴 HIGH | **50.0%** | ❌ FAIL | Every Sunday at 3 AM |
| **Coverage** | On Commit | - | - | **80%** | 🔴 HIGH | **66.7%** | ❌ FAIL | Before every git commit |
| **Backup** | Weekly | 04:00 | Sunday | **85%** | 🔴 HIGH | **100.0%** | ✅ PASS | Every Sunday at 4 AM |
| **Monitoring** | Daily | 07:00 | - | **85%** | 🔴 HIGH | **80.0%** | ❌ FAIL | Every day at 7 AM |
| **Cron** | Daily | 08:00 | - | **80%** | 🟡 MEDIUM | **100.0%** | ✅ PASS | Every day at 8 AM |
| **Frontend** | On Commit | - | - | **75%** | 🟡 MEDIUM | **100.0%** | ✅ PASS | Before every git commit |

**Overall Average Score**: **89.8%**

---

## 🚀 Execution Commands

### Run All Tests
```bash
python manage.py test_runner all
```

### Run Specific Categories
```bash
python manage.py test_runner security database
python manage.py test_runner performance unit
```

### View Latest Results
```bash
python manage.py test_runner --report
```

### Run Scheduled Tests Only
```bash
python manage.py test_runner --schedule
```

---

## ⏰ Automated Scheduling (Cron)

Add to crontab (`crontab -e`):
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

# E2E - Weekly on Sunday at 2 AM
0 2 * * 0 cd /path/to/GRA && python3 manage.py test_runner e2e
```

---

## 📊 Results Storage

### Database
- **Model**: `engine.models.TestResult`
- **Access**: Django admin at `/admin/engine/testresult/`
- **Query**: `TestResult.objects.filter(category='security').order_by('-created_at')`

### JSON Files
- **Location**: `test_results/` directory
- **Format**: `{category}_{timestamp}.json`
- **Purpose**: Historical tracking and backup

---

## 📈 Current Status Summary

- ✅ **4 categories** passing target scores
- ❌ **3 categories** need improvement
- 📊 **85.6%** overall average
- 🎯 **27 total tests** implemented

---

**Last Updated**: November 14, 2025
**Next Run**: See schedule above

