# 🔑 Service Account Key Rotation Guide

## 🚨 URGENT: Your service account key was exposed in git history and must be rotated immediately!

## Step-by-Step Key Rotation

### 1. Access Google Cloud Console
- Go to: https://console.cloud.google.com/
- Select your project: `ultralytics-challange` (or your project ID)

### 2. Navigate to Service Accounts
- Go to: **IAM & Admin** > **Service Accounts**
- Find your service account (likely named something like `yolo-dataset-service`)

### 3. Delete the Compromised Key
- Click on your service account
- Go to the **Keys** tab
- Find the key that was exposed (check the creation date - likely July 21, 2025)
- Click the **Delete** button (🗑️) next to the compromised key
- Confirm deletion

### 4. Create a New Key
- Click **Add Key** > **Create New Key**
- Select **JSON** format
- Click **Create**
- The new key will download automatically

### 5. Secure the New Key
- Move the downloaded key to: `~/.config/gcp/ultralytics-service-account.json`
- Set secure permissions: `chmod 600 ~/.config/gcp/ultralytics-service-account.json`
- Update your `.env` file with the new path

### 6. Test the New Key
```bash
# Test that the new key works
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcp/ultralytics-service-account.json"
python test_environment.py
```

## 🔒 Security Best Practices Going Forward

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data
3. **Store keys outside** the project directory
4. **Set proper file permissions** (600 for keys)
5. **Rotate keys regularly** (every 90 days)
6. **Monitor key usage** in Google Cloud Console

## 📋 Verification Checklist

- [ ] Old key deleted from Google Cloud Console
- [ ] New key created and downloaded
- [ ] New key stored in secure location (`~/.config/gcp/`)
- [ ] File permissions set to 600
- [ ] Environment variables updated
- [ ] Application tested with new key
- [ ] Git history cleaned (no credentials in history)
- [ ] Team notified of the security incident

## 🚨 If You Suspect Unauthorized Access

If you believe the exposed key may have been used maliciously:

1. **Check Cloud Audit Logs** in Google Cloud Console
2. **Review billing** for unexpected charges
3. **Monitor resource usage** for anomalies
4. **Consider rotating all related credentials**
5. **Report the incident** to your security team

## 📞 Support

If you need help with key rotation:
- Google Cloud Support: https://cloud.google.com/support
- Google Cloud Security: https://cloud.google.com/security
