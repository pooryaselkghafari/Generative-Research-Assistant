# Security Fix: Securing Redis and PostgreSQL

## Issue
Redis and PostgreSQL were exposed to the public internet, which is a security risk. These services should only be accessible within the Docker network.

## Solution Applied

### 1. Updated docker-compose.yml
- **Redis**: Removed public port exposure (port 6379)
- **PostgreSQL**: Removed public port exposure (port 5432)
- **Web**: Removed public port exposure (port 8000) - only accessible through nginx

All services can still communicate with each other via Docker's internal network, but are no longer accessible from the internet.

### 2. Apply the Fix

On your server, run:

```bash
cd ~/GRA1

# Pull the updated docker-compose.yml (if using git)
git pull

# Or manually update docker-compose.yml to remove the port mappings

# Restart services to apply changes
docker-compose down
docker-compose up -d

# Verify services are running
docker-compose ps

# Verify ports are no longer exposed
sudo lsof -i :6379  # Should show nothing
sudo lsof -i :5432  # Should show nothing
sudo lsof -i :8000  # Should show nothing (only nginx on 80/443)
```

### 3. Verify Security

```bash
# Test Redis - should fail (connection refused)
telnet 143.198.44.97 6379
# Or:
curl -v telnet://143.198.44.97:6379

# Test PostgreSQL - should fail (connection refused)
telnet 143.198.44.97 5432

# Test from localhost (should also fail unless you bind to 127.0.0.1)
telnet localhost 6379
telnet localhost 5432
```

### 4. Additional Security: Firewall Rules

Even though the ports are no longer exposed, it's good practice to also block them at the firewall level:

```bash
# Check current firewall status
sudo ufw status

# Block Redis and PostgreSQL ports (if not already blocked)
sudo ufw deny 6379/tcp
sudo ufw deny 5432/tcp
sudo ufw deny 8000/tcp

# Reload firewall
sudo ufw reload

# Verify
sudo ufw status
```

### 5. If You Need External Access (Not Recommended)

If you absolutely need external access to these services (e.g., for database management tools), bind them to localhost only:

**For Redis:**
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "127.0.0.1:6379:6379"  # Only accessible from localhost
```

**For PostgreSQL:**
```yaml
db:
  image: postgres:15
  ports:
    - "127.0.0.1:5432:5432"  # Only accessible from localhost
```

Then use SSH tunneling to access them:
```bash
# From your local machine
ssh -L 6379:localhost:6379 deploy@143.198.44.97
ssh -L 5432:localhost:5432 deploy@143.198.44.97
```

## Why This Matters

1. **Redis without authentication**: Redis can be accessed without a password if exposed, allowing attackers to:
   - Read/write data
   - Execute commands
   - Use your server for cryptocurrency mining
   - Delete all data

2. **PostgreSQL exposure**: Database exposure can lead to:
   - Data breaches
   - Unauthorized access
   - Data manipulation or deletion

3. **Best Practice**: Services should only be exposed if they need to be accessed from outside. Since:
   - Redis is only used by your Django app (same Docker network)
   - PostgreSQL is only used by your Django app (same Docker network)
   - Web server is only accessed through nginx (reverse proxy)
   
   None of these need to be publicly accessible.

## Verification Checklist

After applying the fix:

- [ ] docker-compose.yml updated (ports removed)
- [ ] Services restarted
- [ ] Port 6379 not accessible from internet
- [ ] Port 5432 not accessible from internet
- [ ] Port 8000 not accessible from internet (only 80/443 should be)
- [ ] Application still works (services communicate via Docker network)
- [ ] Firewall rules updated (optional but recommended)

## Need Help?

If your application stops working after this change, it means something was trying to access these services from outside the Docker network. Check:

1. **Application logs**: `docker-compose logs web`
2. **Service connectivity**: Services in the same Docker network can still communicate using service names (`redis`, `db`)
3. **Connection strings**: Make sure your Django settings use `redis` and `db` as hostnames (not `localhost`)

