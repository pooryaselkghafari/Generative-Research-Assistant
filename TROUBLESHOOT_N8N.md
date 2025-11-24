# Troubleshooting n8n Blank Page

If you see a blank white page when accessing `/n8n/`, follow these steps:

## Step 1: Check if n8n Container is Running

```bash
docker-compose ps n8n
```

Should show `Up` status. If not, start it:
```bash
docker-compose up -d n8n
```

## Step 2: Check n8n Logs

```bash
docker-compose logs n8n | tail -50
```

Look for errors. Common issues:
- Port 5678 already in use
- Permission errors with volumes
- Missing environment variables

## Step 3: Test n8n Directly

Try accessing n8n directly (bypassing nginx):
```bash
curl http://localhost:5678/
```

If this works, the issue is with nginx configuration.
If this fails, the issue is with n8n itself.

## Step 4: Check Nginx Configuration

```bash
docker-compose exec nginx nginx -t
```

Should show "syntax is ok". If not, fix the configuration.

## Step 5: Check Nginx Logs

```bash
docker-compose logs nginx | grep -i n8n
```

Look for proxy errors.

## Step 6: Verify Environment Variables

Make sure `.env` has:
```bash
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_ENCRYPTION_KEY=<some-value>
```

## Step 7: Restart Services

```bash
docker-compose restart n8n
docker-compose restart nginx
```

## Step 8: Check Browser Console

Open browser DevTools (F12) and check:
- Network tab: Are requests to `/n8n/` returning 200 or errors?
- Console tab: Any JavaScript errors?

## Common Fixes

### Fix 1: Remove N8N_PATH from docker-compose.yml

The `N8N_PATH` environment variable should NOT be set. n8n should run at root, and nginx handles the `/n8n/` path routing.

### Fix 2: Ensure n8n is on Host Network

In `docker-compose.yml`, n8n should have:
```yaml
network_mode: "host"
```

### Fix 3: Check Port Conflicts

Make sure port 5678 is not used by another service:
```bash
netstat -tuln | grep 5678
# or
lsof -i :5678
```

### Fix 4: Clear n8n Data (Last Resort)

If n8n data is corrupted:
```bash
docker-compose down
docker volume rm gra_n8n_data
docker-compose up -d n8n
```

**Warning**: This will delete all n8n workflows!

## Still Not Working?

1. Check if middleware is blocking: Look for redirects in browser network tab
2. Try accessing n8n without path: `http://localhost:5678/` (should show n8n login)
3. Check Django logs: `docker-compose logs web | grep -i n8n`
4. Verify admin authentication: Make sure you're logged in as admin user

