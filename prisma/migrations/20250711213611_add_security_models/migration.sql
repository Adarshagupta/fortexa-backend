-- CreateEnum
CREATE TYPE "SecurityEventType" AS ENUM ('LOGIN_SUCCESS', 'LOGIN_FAILURE', 'MULTIPLE_FAILED_LOGINS', 'SUSPICIOUS_LOGIN_PATTERN', 'UNUSUAL_LOCATION', 'BRUTE_FORCE_DETECTED', 'ACCOUNT_LOCKED', 'ACCOUNT_UNLOCKED', 'IP_BLACKLISTED', 'DEVICE_CHANGED', 'MFA_FAILED', 'MFA_BYPASSED', 'SESSION_HIJACKED', 'CONCURRENT_SESSIONS', 'PASSWORD_CHANGED', 'EMAIL_CHANGED', 'SECURITY_QUESTION_FAILED', 'SUSPICIOUS_USER_AGENT', 'VPN_DETECTED', 'TOR_DETECTED', 'COMPROMISED_CREDENTIALS');

-- CreateEnum
CREATE TYPE "SecuritySeverity" AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');

-- CreateEnum
CREATE TYPE "IpReputation" AS ENUM ('TRUSTED', 'UNKNOWN', 'SUSPICIOUS', 'MALICIOUS');

-- CreateEnum
CREATE TYPE "SecurityRuleType" AS ENUM ('IP_BASED', 'USER_BEHAVIOR', 'DEVICE_BASED', 'GEOGRAPHIC', 'TIME_BASED', 'PATTERN_BASED');

-- CreateEnum
CREATE TYPE "SecurityAction" AS ENUM ('LOG_ONLY', 'REQUIRE_MFA', 'BLOCK_REQUEST', 'LOCK_ACCOUNT', 'ALERT_ADMIN', 'BLACKLIST_IP', 'REQUIRE_VERIFICATION');

-- CreateEnum
CREATE TYPE "RateLimitType" AS ENUM ('IP_LOGIN', 'USER_LOGIN', 'IP_GLOBAL', 'USER_GLOBAL', 'IP_API', 'USER_API');

-- AlterTable
ALTER TABLE "user_sessions" ADD COLUMN     "city" TEXT,
ADD COLUMN     "country" TEXT,
ADD COLUMN     "deviceFingerprint" TEXT,
ADD COLUMN     "isSuspicious" BOOLEAN NOT NULL DEFAULT false,
ADD COLUMN     "location" TEXT,
ADD COLUMN     "riskScore" DOUBLE PRECISION NOT NULL DEFAULT 0.0;

-- AlterTable
ALTER TABLE "users" ADD COLUMN     "accountLockedUntil" TIMESTAMP(3),
ADD COLUMN     "failedLoginAttempts" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "lastLoginIp" TEXT,
ADD COLUMN     "riskScore" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
ADD COLUMN     "suspiciousActivityCount" INTEGER NOT NULL DEFAULT 0;

-- CreateTable
CREATE TABLE "login_attempts" (
    "id" TEXT NOT NULL,
    "userId" TEXT,
    "email" TEXT NOT NULL,
    "ipAddress" TEXT NOT NULL,
    "userAgent" TEXT,
    "deviceFingerprint" TEXT,
    "location" TEXT,
    "country" TEXT,
    "city" TEXT,
    "isSuccessful" BOOLEAN NOT NULL,
    "failureReason" TEXT,
    "riskScore" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "isBlocked" BOOLEAN NOT NULL DEFAULT false,
    "isSuspicious" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "login_attempts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "security_events" (
    "id" TEXT NOT NULL,
    "userId" TEXT,
    "eventType" "SecurityEventType" NOT NULL,
    "severity" "SecuritySeverity" NOT NULL,
    "description" TEXT NOT NULL,
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "location" TEXT,
    "metadata" JSONB,
    "isResolved" BOOLEAN NOT NULL DEFAULT false,
    "resolvedAt" TIMESTAMP(3),
    "resolvedBy" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "security_events_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "ip_addresses" (
    "id" TEXT NOT NULL,
    "ipAddress" TEXT NOT NULL,
    "country" TEXT,
    "city" TEXT,
    "region" TEXT,
    "timezone" TEXT,
    "latitude" DOUBLE PRECISION,
    "longitude" DOUBLE PRECISION,
    "isp" TEXT,
    "organization" TEXT,
    "isBlacklisted" BOOLEAN NOT NULL DEFAULT false,
    "isWhitelisted" BOOLEAN NOT NULL DEFAULT false,
    "riskScore" DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    "reputation" "IpReputation" NOT NULL DEFAULT 'UNKNOWN',
    "loginAttempts" INTEGER NOT NULL DEFAULT 0,
    "failedLogins" INTEGER NOT NULL DEFAULT 0,
    "lastLoginAt" TIMESTAMP(3),
    "isVpn" BOOLEAN NOT NULL DEFAULT false,
    "isProxy" BOOLEAN NOT NULL DEFAULT false,
    "isTor" BOOLEAN NOT NULL DEFAULT false,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ip_addresses_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "trusted_devices" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "deviceFingerprint" TEXT NOT NULL,
    "deviceName" TEXT,
    "deviceType" TEXT,
    "browser" TEXT,
    "operatingSystem" TEXT,
    "ipAddress" TEXT,
    "location" TEXT,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "lastUsedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "trustedUntil" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "trusted_devices_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "security_rules" (
    "id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "ruleType" "SecurityRuleType" NOT NULL,
    "condition" JSONB NOT NULL,
    "action" "SecurityAction" NOT NULL,
    "isActive" BOOLEAN NOT NULL DEFAULT true,
    "priority" INTEGER NOT NULL DEFAULT 100,
    "triggeredCount" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "security_rules_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rate_limit_rules" (
    "id" TEXT NOT NULL,
    "identifier" TEXT NOT NULL,
    "ruleType" "RateLimitType" NOT NULL,
    "maxAttempts" INTEGER NOT NULL,
    "windowMinutes" INTEGER NOT NULL,
    "currentAttempts" INTEGER NOT NULL DEFAULT 0,
    "windowStart" TIMESTAMP(3) NOT NULL,
    "isBlocked" BOOLEAN NOT NULL DEFAULT false,
    "blockedUntil" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "rate_limit_rules_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "login_attempts_email_createdAt_idx" ON "login_attempts"("email", "createdAt");

-- CreateIndex
CREATE INDEX "login_attempts_ipAddress_createdAt_idx" ON "login_attempts"("ipAddress", "createdAt");

-- CreateIndex
CREATE INDEX "login_attempts_isSuccessful_createdAt_idx" ON "login_attempts"("isSuccessful", "createdAt");

-- CreateIndex
CREATE INDEX "security_events_userId_createdAt_idx" ON "security_events"("userId", "createdAt");

-- CreateIndex
CREATE INDEX "security_events_eventType_createdAt_idx" ON "security_events"("eventType", "createdAt");

-- CreateIndex
CREATE INDEX "security_events_severity_createdAt_idx" ON "security_events"("severity", "createdAt");

-- CreateIndex
CREATE UNIQUE INDEX "ip_addresses_ipAddress_key" ON "ip_addresses"("ipAddress");

-- CreateIndex
CREATE UNIQUE INDEX "trusted_devices_userId_deviceFingerprint_key" ON "trusted_devices"("userId", "deviceFingerprint");

-- CreateIndex
CREATE UNIQUE INDEX "rate_limit_rules_identifier_ruleType_key" ON "rate_limit_rules"("identifier", "ruleType");

-- AddForeignKey
ALTER TABLE "login_attempts" ADD CONSTRAINT "login_attempts_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "security_events" ADD CONSTRAINT "security_events_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE SET NULL ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "trusted_devices" ADD CONSTRAINT "trusted_devices_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
