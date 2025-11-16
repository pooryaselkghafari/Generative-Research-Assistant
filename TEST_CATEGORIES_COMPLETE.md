# Complete Test Categories Reference

## 📊 All Test Categories

### Original Categories (7)
1. **Security** - Authentication, authorization, data isolation
2. **Database** - Query performance, integrity, constraints
3. **Performance** - Response times, query efficiency
4. **Unit** - Service layer, helper functions
5. **Integration** - Complete workflows
6. **API** - API endpoints
7. **E2E** - End-to-end user flows

### New Categories (7)
8. **Static Analysis** - Code quality, syntax, security patterns
9. **Dependency Scan** - Vulnerability scanning
10. **Coverage** - Code coverage percentage
11. **Backup** - Backup/restore functionality
12. **Monitoring** - Logging and monitoring
13. **Cron** - Scheduled tasks
14. **Frontend** - Templates, static files, JavaScript

---

## 📋 Complete Schedule Table

| Category | Interval | Time | Day | Target | Priority |
|----------|----------|------|-----|--------|----------|
| Security | Daily | 02:00 | - | 95% | 🔴 HIGH |
| Database | Daily | 03:00 | - | 85% | 🔴 HIGH |
| Performance | Daily | 04:00 | - | 80% | 🟡 MEDIUM |
| Unit | On Commit | - | - | 80% | 🔴 HIGH |
| Integration | Daily | 05:00 | - | 75% | 🟡 MEDIUM |
| API | Daily | 06:00 | - | 80% | 🟡 MEDIUM |
| E2E | Weekly | 02:00 | Sunday | 70% | 🟢 LOW |
| Static Analysis | On Commit | - | - | 80% | 🔴 HIGH |
| Dependency Scan | Weekly | 03:00 | Sunday | 95% | 🔴 HIGH |
| Coverage | On Commit | - | - | 80% | 🔴 HIGH |
| Backup | Weekly | 04:00 | Sunday | 85% | 🔴 HIGH |
| Monitoring | Daily | 07:00 | - | 85% | 🔴 HIGH |
| Cron | Daily | 08:00 | - | 80% | 🟡 MEDIUM |
| Frontend | On Commit | - | - | 75% | 🟡 MEDIUM |

---

## 🚀 Quick Commands

```bash
# Run all tests
python manage.py test_runner all

# Run on-commit tests
python manage.py test_runner unit static_analysis coverage frontend

# Run weekly tests
python manage.py test_runner e2e dependency_scan backup

# Run high-priority tests
python manage.py test_runner security database dependency_scan backup monitoring

# View report
python manage.py test_runner --report
```

---

**Total Categories**: 14
**Total Tests**: 50+ individual tests
**Last Updated**: November 14, 2025


