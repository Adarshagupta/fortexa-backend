-- AlterTable
ALTER TABLE "users" ADD COLUMN     "emailVerificationOtp" TEXT,
ADD COLUMN     "emailVerificationOtpExpiry" TIMESTAMP(3);
