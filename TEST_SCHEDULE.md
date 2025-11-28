# Test Execution Schedule & Results Tracking

## 📋 Test Schedule Table

| Category | Interval | Time | Day | Target Score | Priority | Status |
|----------|----------|------|-----|--------------|----------|--------|
| **Security** | Daily | 02:00 | - | 95% | 🔴 HIGH | ✅ Active |
| **Database** | Daily | 03:00 | - | 85% | 🔴 HIGH | ✅ Active |
| **Performance** | Daily | 04:00 | - | 80% | 🟡 MEDIUM | ✅ Active |
| **Unit** | On Commit | - | - | 80% | 🔴 HIGH | ✅ Active |
| **Integration** | Daily | 05:00 | - | 75% | 🟡 MEDIUM | ✅ Active |
| **API** | Daily | 06:00 | - | 80% | 🟡 MEDIUM | ✅ Active |
| **E2E** | Weekly | 02:00 | Sunday | 70% | 🟢 LOW | ✅ Active |

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

### Run Scheduled Tests Only
```bash
python manage.py test_runner --schedule
```

### View Test Report
```bash
python manage.py test_runner --report
```

### Run Individual Test Suites
```bash
python manage.py test tests.security.test_security
python manage.py test tests.database.test_database
python manage.py test tests.performance.test_performance
python manage.py test tests.unit.test_services
python manage.py test tests.integration.test_integration
python manage.py test tests.api.test_api
python manage.py test tests.e2e.test_e2e
```

---

## ⏰ Automated Scheduling (Cron Jobs)

### Setup Cron Jobs
```bash
# Edit crontab
crontab -e

# Add these lines (adjust path to your project):
0 2 * * * cd /path/to/GRA && /usr/bin/python3 manage.py test_runner security >> /var/log/statbox_tests.log 2>&1
0 3 * * * cd /path/to/GRA && /usr/bin/python3 manage.py test_runner database >> /var/log/statbox_tests.log 2>&1
0 4 * * * cd /path/to/GRA && /usr/bin/python3 manage.py test_runner performance >> /var/log/statbox_tests.log 2>&1
0 5 * * * cd /path/to/GRA && /usr/bin/python3 manage.py test_runner integration >> /var/log/statbox_tests.log 2>&1
0 6 * * * cd /path/to/GRA && /usr/bin/python3 manage.py test_runner api >> /var/log/statbox_tests.log 2>&1
0 2 * * 0 cd /path/to/GRA && /usr/bin/python3 manage.py test_runner e2e >> /var/log/statbox_tests.log 2>&1
```

### Pre-Commit Hook (for Unit Tests)
Create `.git/hooks/pre-commit`:
```bash
#!/bin/sh
cd /path/to/GRA
python manage.py test_runner unit
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed. Commit aborted."
    exit 1
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## 📊 Test Results Storage

### Database Storage
- **Model**: `engine.models.TestResult`
- **Location**: Main database (persistent)
- **Access**: Django admin or Python shell

### File Storage
- **Location**: `test_results/` directory
- **Format**: JSON files (`{category}_{timestamp}.json`)
- **Purpose**: Backup and historical tracking

### View Results

#### Via Django Admin
1. Go to `/admin/`
2. Navigate to "Engine" → "Test Results"
3. Filter by category, date, or pass/fail status

#### Via Python Shell
```python
from engine.models import TestResult

# Get latest results
for category in ['security', 'database', 'performance', 'unit', 'integration', 'api', 'e2e']:
    latest = TestResult.objects.filter(category=category).order_by('-created_at').first()
    if latest:
        print(f"{category}: {latest.score:.1f}% ({'✅' if latest.passed else '❌'})")
```

#### Via Command Line
```bash
python manage.py test_runner --report
```

---

## 📈 Current Test Results

Run `python manage.py test_runner --report` to see the latest results.

---

## 🎯 Target Scores & Interpretation

| Score Range | Status | Action Required |
|-------------|--------|-----------------|
| 90-100% | ✅ Excellent | None - maintain |
| 80-89% | 🟢 Good | Monitor - minor improvements |
| 70-79% | 🟡 Needs Work | Review and improve |
| <70% | 🔴 Critical | Immediate action required |

---

## 📝 Test Categories Explained

### Security Tests (Target: 95%)
- User authentication and authorization
- Data isolation between users
- CSRF protection
- SQL injection prevention
- File upload security
- API endpoint security

### Database Tests (Target: 85%)
- Query performance (N+1 prevention)
- Database integrity (foreign keys, unique constraints)
- Transaction rollback
- Index usage
- Data consistency

### Performance Tests (Target: 80%)
- Page load times (<2s)
- API response times (<500ms)
- Database query efficiency
- Concurrent request handling

### Unit Tests (Target: 80%)
- Service layer functions
- Helper functions
- Model methods
- Individual component testing

### Integration Tests (Target: 75%)
- Complete workflows
- Service interactions
- End-to-end data flow
- Error handling across components

### API Tests (Target: 80%)
- Endpoint functionality
- Authentication requirements
- Response formats
- Error handling

### E2E Tests (Target: 70%)
- User registration flow
- Login flow
- Complete user journeys
- UI interactions

---

## 🔄 Continuous Improvement

### After Each Test Run
1. Review failed tests
2. Fix issues immediately
3. Update tests if requirements change
4. Monitor score trends

### Weekly Review
1. Check overall score trends
2. Identify patterns in failures
3. Update test coverage
4. Adjust target scores if needed

### Monthly Review
1. Comprehensive test suite review
2. Add new test cases
3. Remove obsolete tests
4. Update documentation

---

## 📞 Support

For issues with tests:
1. Check test logs in `test_results/` directory
2. Review Django test output
3. Check database for TestResult entries
4. Verify cron jobs are running (if automated)

---

**Last Updated**: November 14, 2025
**Test Framework Version**: 1.0



