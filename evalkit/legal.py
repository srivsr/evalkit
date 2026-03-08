"""Legal document endpoints for EvalKit — Privacy, Terms, Refund."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/v1/legal", tags=["legal"])


class LegalDocument(BaseModel):
    title: str
    slug: str
    content: str
    effective_date: str
    last_updated: str


class LegalIndex(BaseModel):
    documents: list[dict]


EFFECTIVE_DATE = "2026-02-19"
LAST_UPDATED = "2026-02-19"

PRIVACY_POLICY = """## 1. Introduction

EvalKit ("we," "us," "our") is an AI evaluation platform that helps developers and teams assess, benchmark, and monitor the quality of AI/LLM outputs. This Privacy Policy describes how we collect, use, store, and protect your information when you use our website, API, and services (collectively, the "Service").

By using EvalKit, you agree to the collection and use of information in accordance with this policy.

## 2. Information We Collect

### 2.1 Account Information

When you create an account, we collect:

- **Email address** — provided via Clerk authentication
- **Name** — as provided by your authentication provider
- **User ID** — a unique identifier assigned by our authentication provider (Clerk)

### 2.2 Usage Data

We automatically collect:

- **Evaluation data** — the prompts, responses, and evaluation results you submit through the Service. This is the core data you provide for AI quality assessment.
- **Project metadata** — project names, settings, and configuration you create within the Service.
- **API usage metrics** — request counts, timestamps, evaluation types, and quota consumption.
- **Technical data** — IP address, browser type, device information, and access timestamps for security and performance monitoring.

### 2.3 Payment Information

When you subscribe to a paid plan, we collect:

- **Subscription tier** selected (Basic or Pro)
- **Payment provider** used (PayPal, Razorpay, or Payoneer)
- **Transaction IDs** — order and payment identifiers from your payment provider

**We do NOT collect or store**: credit card numbers, bank account numbers, CVVs, or any sensitive payment credentials. All payment processing is handled directly by our third-party payment providers (PayPal, Razorpay, Payoneer). We only receive transaction confirmation and identifiers.

### 2.4 Information We Do NOT Collect

- We do not collect biometric data
- We do not collect location data beyond IP-derived country
- We do not track you across other websites
- We do not collect information from minors (see Section 8)

## 3. How We Use Your Information

We use the information we collect to:

- Provide the Service (account info, evaluation data)
- Process payments (payment transaction data)
- Enforce usage quotas (API usage metrics)
- Send service notifications (email address)
- Prevent abuse and fraud (technical data, usage patterns)
- Improve the Service (aggregated, anonymized usage data)
- Respond to support requests (account info, usage data)

**We do NOT:**
- Sell your personal information to third parties
- Use your evaluation data to train AI models
- Share your data with advertisers
- Profile you for targeted advertising

## 4. Data Storage and Security

### 4.1 Where We Store Data

- **Application data** is stored on servers hosted in the United States via AWS (Amazon Web Services)
- **Authentication data** is managed by Clerk (https://clerk.com), headquartered in the United States
- **Payment data** is processed and stored by your chosen payment provider (PayPal, Razorpay, or Payoneer) in accordance with their respective privacy policies

### 4.2 How We Protect Data

We implement the following security measures:

- All data transmitted between your browser and our servers is encrypted using TLS 1.2 or higher (HTTPS)
- Database access is restricted and authenticated
- API endpoints require authentication via bearer tokens
- Payment credentials are never transmitted through or stored on our servers
- Regular security reviews of our codebase and infrastructure

### 4.3 Data Retention

- Account information: Until you delete your account
- Evaluation data: Until you delete the project or account
- Payment transaction records: 7 years (legal/tax requirements)
- Server access logs: 90 days
- Aggregated analytics: Indefinite (anonymized)

## 5. Data Sharing

We share your information only in the following circumstances:

### 5.1 Service Providers

We use the following third-party services to operate EvalKit:

- **Clerk** — Authentication (email, name, login events)
- **PayPal** — Payment processing (transaction amount, email)
- **Razorpay** — Payment processing, India (transaction amount, email)
- **Payoneer** — Payment processing (transaction amount, email)
- **AWS** — Infrastructure/hosting (all application data, encrypted)
- **OpenAI / Anthropic** — Judge model providers (evaluation prompts and responses you submit)

### 5.2 Legal Requirements

We may disclose your information if required to do so by law, or in the good faith belief that such action is necessary to comply with a legal obligation, protect our rights, or ensure the safety of users.

### 5.3 Business Transfers

If SriVSR is involved in a merger, acquisition, or sale of assets, your information may be transferred as part of that transaction. We will notify you via email or prominent notice on the Service before your information becomes subject to a different privacy policy.

### 5.4 With Your Consent

We may share information with third parties when you explicitly consent to such sharing.

## 6. Your Rights

### 6.1 All Users

Regardless of your location, you have the right to:

- **Access** — Request a copy of the personal information we hold about you
- **Correction** — Request correction of inaccurate personal information
- **Deletion** — Request deletion of your account and associated data
- **Data Export** — Request a machine-readable export of your data (evaluation results, project data)
- **Objection** — Object to processing of your data for specific purposes
- **Withdraw Consent** — Withdraw consent where processing is based on consent

### 6.2 For Users in the European Economic Area (EEA)

If you are in the EEA, you additionally have rights under the General Data Protection Regulation (GDPR), including the right to lodge a complaint with your local supervisory authority.

### 6.3 For Users in California (USA)

California residents have additional rights under the California Consumer Privacy Act (CCPA), including the right to know what personal information is collected and the right to opt out of the sale of personal information. We do not sell personal information.

### 6.4 For Users in India

Your rights are governed by the Digital Personal Data Protection Act, 2023 (DPDPA) where applicable. You may exercise your rights by contacting us at the address below.

### 6.5 How to Exercise Your Rights

To exercise any of these rights, email us at **admin@srivsr.com** with the subject line "Privacy Request — [Your Request Type]". We will respond within 30 days.

## 7. Cookies and Tracking

EvalKit uses only **essential cookies** required for:

- Authentication session management (via Clerk)
- CSRF protection

We do NOT use:
- Analytics cookies (no Google Analytics, no Mixpanel)
- Advertising cookies
- Third-party tracking pixels
- Social media tracking widgets

## 8. Children's Privacy

EvalKit is not intended for use by individuals under the age of 16. We do not knowingly collect personal information from children under 16. If you become aware that a child has provided us with personal information, please contact us and we will take steps to delete such information.

## 9. International Data Transfers

Your information may be transferred to and processed in the United States, where our servers and service providers are located. By using EvalKit, you consent to such transfer. We ensure appropriate safeguards are in place for international transfers.

## 10. Changes to This Policy

We may update this Privacy Policy from time to time. We will notify you of material changes by:
- Posting the updated policy on our website with a new "Last Updated" date
- Sending an email notification for significant changes

Your continued use of the Service after changes constitutes acceptance of the updated policy.

## 11. Contact

For privacy-related questions or requests:

**Email**: admin@srivsr.com
**Subject**: Privacy Inquiry — EvalKit
**Response Time**: Within 30 days

**Company**: SriVSR (Individual Proprietorship)
**Location**: Tamil Nadu, India"""

TERMS_OF_SERVICE = """## 1. Acceptance of Terms

By accessing or using EvalKit ("Service"), you agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, do not use the Service.

These Terms constitute a legally binding agreement between you ("User," "you," "your") and SriVSR ("Company," "we," "us," "our"), the operator of EvalKit.

## 2. Description of Service

EvalKit is an AI evaluation platform that enables users to:
- Create evaluation projects for assessing AI/LLM output quality
- Run automated evaluations using judge models (faithfulness, relevance, answer quality, etc.)
- Track evaluation results, detect regressions, and monitor AI quality over time
- Access evaluation functionality via web interface, API, and CLI

## 3. Account Registration and Eligibility

### 3.1 Eligibility

You must be at least 16 years of age to use EvalKit. By creating an account, you represent that you meet this requirement.

### 3.2 Account Security

You are responsible for:
- Maintaining the confidentiality of your authentication credentials
- All activities that occur under your account
- Notifying us immediately of any unauthorized use of your account

We use Clerk for authentication. Your login credentials are managed by Clerk's security infrastructure, not stored directly by EvalKit.

### 3.3 Accurate Information

You agree to provide accurate, current, and complete information during registration and to update such information to keep it accurate.

## 4. Subscription Plans and Payment

### 4.1 Plans

EvalKit offers the following subscription tiers:

- **Free** — $0/month, 50 evaluations/month, 3 projects, GPT-4o Mini
- **Basic** — $19/month, 500 evaluations/month, 10 projects, GPT-4o + Claude Sonnet
- **Pro** — $49/month, 5,000 evaluations/month, unlimited projects, all available models

### 4.2 Billing

- All paid plans are billed **monthly** in **US Dollars (USD)**
- Payment is processed at the time of subscription through your chosen provider: PayPal, Razorpay, or Payoneer
- Your subscription begins immediately upon successful payment
- Each subscription period is **30 days** from the date of purchase

### 4.3 Price Changes

We reserve the right to change subscription prices. Price changes will:
- Be communicated via email at least 30 days before taking effect
- Apply only to future billing periods, not current active subscriptions
- Not affect users who have already paid for the current period

### 4.4 Payment Providers

Payments are processed by third-party providers. By making a payment, you also agree to the terms of your chosen provider:
- **PayPal**: https://www.paypal.com/legalhub
- **Razorpay**: https://razorpay.com/terms/
- **Payoneer**: https://www.payoneer.com/legal/

### 4.5 Taxes

Listed prices do not include applicable taxes. You are responsible for any taxes, duties, or government-imposed charges associated with your use of the Service, based on your jurisdiction.

## 5. Usage Limits and Fair Use

### 5.1 Quota Enforcement

Each subscription tier includes monthly evaluation limits as described in Section 4.1. When you reach your monthly limit:
- Further evaluation requests will return an HTTP 429 error
- Your evaluation quota resets at the beginning of each calendar month (UTC)
- Unused evaluations do not roll over to the next month

### 5.2 Project Limits

Each tier has a maximum number of projects you can create. You may delete existing projects to create new ones within your limit.

### 5.3 Fair Use

You agree not to:
- Use automated systems to circumvent usage quotas
- Share account credentials to allow multiple individuals to use a single account
- Use the Service to compete directly with EvalKit by reselling evaluation results
- Reverse-engineer the Service or its evaluation algorithms

### 5.4 API Usage

If you access EvalKit via API:
- You must include valid authentication headers with each request
- Rate limiting may be applied to prevent abuse
- API keys and tokens are confidential and must not be shared publicly

## 6. Intellectual Property

### 6.1 Your Data

You retain full ownership of all data you upload to or create within EvalKit, including:
- Evaluation prompts, contexts, and responses
- Project configurations and settings
- Evaluation results and metrics

### 6.2 Our Service

EvalKit, including its software, design, documentation, and proprietary evaluation algorithms, is owned by SriVSR. These Terms do not grant you any rights to our intellectual property beyond the right to use the Service as described.

### 6.3 License to Use Your Data

By submitting data to EvalKit, you grant us a limited, non-exclusive license to process your data solely for the purpose of providing the Service. We do not use your data for AI model training or any purpose beyond delivering the Service to you.

### 6.4 Feedback

If you provide feedback, suggestions, or ideas about the Service, you grant us a royalty-free, perpetual, irrevocable license to use such feedback for any purpose without obligation to you.

## 7. Limitation of Liability

### 7.1 Service Provided "As Is"

EvalKit is provided "as is" and "as available" without warranties of any kind, either express or implied, including but not limited to implied warranties of merchantability, fitness for a particular purpose, and non-infringement.

### 7.2 No Guarantee of Results

Evaluation results generated by EvalKit are based on AI judge models and are intended to provide insights, not definitive quality assessments. We do not guarantee the accuracy, completeness, or reliability of evaluation results.

### 7.3 Limitation of Damages

To the maximum extent permitted by law, SriVSR shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of profits or revenues, whether incurred directly or indirectly.

Our total aggregate liability for any claims arising out of or related to these Terms or the Service shall not exceed the amount you paid us in the 12 months preceding the claim.

### 7.4 Third-Party Services

EvalKit integrates with third-party AI model providers (OpenAI, Anthropic, etc.) for judge model evaluations. We are not responsible for the availability, accuracy, or terms of these third-party services.

## 8. Acceptable Use

You agree NOT to use EvalKit to:

- Violate any applicable law or regulation
- Process, store, or transmit any content that is illegal, harmful, threatening, abusive, defamatory, or otherwise objectionable
- Attempt to gain unauthorized access to the Service, other accounts, or related systems
- Interfere with or disrupt the Service or servers
- Upload malicious code, viruses, or harmful data
- Use the Service for cryptocurrency mining or unrelated computational purposes
- Impersonate any person or entity
- Harvest or collect user information without consent

Violation of acceptable use policies may result in immediate account termination without refund.

## 9. Account Termination

### 9.1 By You

You may cancel your subscription and delete your account at any time by:
- Contacting us at admin@srivsr.com
- Using the account deletion feature in the Service (when available)

Upon cancellation:
- Your access to paid features will continue until the end of the current billing period
- Your data will be retained for 30 days after account deletion, then permanently removed
- Payment transaction records will be retained for 7 years per legal requirements

### 9.2 By Us

We reserve the right to suspend or terminate your account if you:
- Violate these Terms or the Acceptable Use policy
- Engage in fraudulent payment activity
- Fail to pay subscription fees when due
- Pose a risk to the Service, other users, or our infrastructure

We will make reasonable efforts to notify you before termination, except in cases of egregious violations.

## 10. Dispute Resolution

### 10.1 Governing Law

These Terms are governed by the laws of **India**, without regard to conflict of law principles.

### 10.2 Informal Resolution

Before filing any formal legal proceeding, you agree to attempt to resolve disputes informally by contacting us at admin@srivsr.com. We will attempt to resolve the dispute within 30 days.

### 10.3 Jurisdiction

Any legal proceedings arising out of or related to these Terms shall be subject to the exclusive jurisdiction of the courts in **Chennai, Tamil Nadu, India**.

### 10.4 Arbitration

For disputes that cannot be resolved informally, both parties agree to resolve the matter through binding arbitration in Chennai, India, under the Arbitration and Conciliation Act, 1996.

## 11. Service Availability

### 11.1 Uptime

We strive to maintain high availability but do not guarantee uninterrupted service. The Service may be temporarily unavailable due to:
- Scheduled maintenance (we will provide advance notice when possible)
- Unplanned outages or infrastructure failures
- Third-party service disruptions (Clerk, AI providers, payment providers)

### 11.2 Modifications

We may modify, update, or discontinue features of the Service at any time. Material changes that reduce functionality of paid plans will be communicated with at least 30 days' notice.

## 12. Indemnification

You agree to indemnify and hold harmless SriVSR, its owner, affiliates, and service providers from any claims, damages, losses, or expenses (including legal fees) arising from:
- Your use of the Service
- Your violation of these Terms
- Your violation of any third-party rights
- Data you submit to the Service

## 13. Miscellaneous

### 13.1 Entire Agreement

These Terms, together with the Privacy Policy and Refund Policy, constitute the entire agreement between you and SriVSR regarding the Service.

### 13.2 Severability

If any provision of these Terms is found to be unenforceable, the remaining provisions will continue in full effect.

### 13.3 No Waiver

Our failure to enforce any right or provision of these Terms does not constitute a waiver of such right or provision.

### 13.4 Assignment

You may not assign your rights under these Terms without our prior written consent. We may assign our rights without restriction.

## 14. Contact

For questions about these Terms:

**Email**: admin@srivsr.com
**Subject**: Terms Inquiry — EvalKit
**Company**: SriVSR (Individual Proprietorship)
**Location**: Tamil Nadu, India"""

REFUND_POLICY = """## 1. Overview

We want you to be satisfied with EvalKit. This Refund Policy explains when and how you can request a refund for paid subscriptions.

## 2. Free Plan

The Free plan has no cost and therefore no refund applies. You can use the Free plan indefinitely without any payment obligation.

## 3. Paid Plans (Basic and Pro)

### 3.1 7-Day Money-Back Guarantee

We offer a **7-day money-back guarantee** on all paid subscriptions for **first-time subscribers**:

- If you are unhappy with your paid plan for any reason, you may request a full refund within **7 calendar days** of your initial subscription purchase
- This guarantee applies only to your **first** subscription purchase with EvalKit
- Subsequent subscription renewals or plan upgrades are not eligible for the money-back guarantee

### 3.2 Eligibility for Refund

You are eligible for a refund if:

- First-time subscription, requested within 7 days — Yes
- Service was significantly unavailable during your subscription period (more than 72 hours continuous downtime) — Yes
- You were charged incorrectly or billed for a plan you did not select — Yes
- Duplicate payment was processed — Yes
- You changed your mind after 7 days — No
- You used a significant portion of your monthly quota before requesting — See 3.3
- Account was terminated for Terms of Service violation — No
- Price changed and you don't wish to continue — See 3.4

### 3.3 Partial Usage Consideration

If you have used more than **50% of your monthly evaluation quota** before requesting a refund within the 7-day window, we reserve the right to issue a **partial refund** proportional to unused quota, or decline the refund at our discretion.

### 3.4 Price Changes

If we increase the price of your subscription plan:
- You will be notified at least 30 days in advance
- If you cancel before the new price takes effect, you will not be charged the new rate
- If you have already been charged at the new rate and did not consent to the increase, you may request a full refund for that billing period

## 4. How to Request a Refund

### Step 1: Send an Email

Email **admin@srivsr.com** with the subject line: **"Refund Request — EvalKit"**

Include the following information:
- Your registered email address
- Your subscription plan (Basic or Pro)
- Payment provider used (PayPal, Razorpay, or Payoneer)
- Date of purchase
- Reason for refund request (helps us improve the Service)
- Order ID or transaction ID (if available)

### Step 2: We Review

We will acknowledge your request within **2 business days** and review it against this policy.

### Step 3: Refund Processed

If approved:
- Refunds are processed through the **same payment method** you used for the original purchase
- Processing times depend on your payment provider:
  - PayPal: 3–5 business days
  - Razorpay: 5–7 business days
  - Payoneer: 7–10 business days

**Note**: Actual refund timelines depend on your bank or payment provider and may vary.

## 5. What Happens After a Refund

Once a refund is processed:

- Your account will be **downgraded to the Free plan** immediately
- You will retain access to your projects and data, but usage limits will revert to Free tier quotas (50 evaluations/month, 3 projects)
- Any evaluations you ran during the paid subscription period will remain in your history
- You may re-subscribe to a paid plan at any time

## 6. Subscription Cancellation (Without Refund)

If you wish to cancel your subscription without requesting a refund:

- Your paid features remain active until the **end of the current billing period**
- After the billing period ends, your account automatically reverts to the Free plan
- No further charges will be applied
- To cancel, email **admin@srivsr.com** with the subject "Cancel Subscription — EvalKit"

## 7. Chargebacks and Disputes

We strongly encourage you to contact us directly at **admin@srivsr.com** before initiating a chargeback or payment dispute with your bank or payment provider.

If a chargeback is filed:
- We will cooperate with the payment provider's dispute resolution process
- We may suspend your account during the investigation
- Fraudulent chargebacks may result in permanent account termination

## 8. Exceptions and Special Circumstances

We evaluate refund requests on a case-by-case basis. Special circumstances that may warrant exceptions include:
- Extended service outages that materially impacted your ability to use the Service
- Technical issues on our end that prevented you from accessing paid features
- Billing errors or unauthorized charges

For any special circumstances, please email us with details and we will do our best to find a fair resolution.

## 9. Changes to This Policy

We may update this Refund Policy from time to time. Material changes will be communicated via email. The version in effect at the time of your purchase applies to that transaction.

## 10. Contact

For refund requests or billing questions:

**Email**: admin@srivsr.com
**Subject**: Refund Request — EvalKit
**Response Time**: Within 2 business days

**Company**: SriVSR (Individual Proprietorship)
**Location**: Tamil Nadu, India"""


@router.get("/privacy", response_model=LegalDocument)
async def get_privacy_policy():
    return LegalDocument(
        title="Privacy Policy",
        slug="privacy",
        content=PRIVACY_POLICY,
        effective_date=EFFECTIVE_DATE,
        last_updated=LAST_UPDATED,
    )


@router.get("/terms", response_model=LegalDocument)
async def get_terms_of_service():
    return LegalDocument(
        title="Terms of Service",
        slug="terms",
        content=TERMS_OF_SERVICE,
        effective_date=EFFECTIVE_DATE,
        last_updated=LAST_UPDATED,
    )


@router.get("/refund", response_model=LegalDocument)
async def get_refund_policy():
    return LegalDocument(
        title="Refund Policy",
        slug="refund",
        content=REFUND_POLICY,
        effective_date=EFFECTIVE_DATE,
        last_updated=LAST_UPDATED,
    )


@router.get("", response_model=LegalIndex)
async def list_legal_documents():
    return LegalIndex(documents=[
        {"title": "Privacy Policy", "slug": "privacy", "url": "/v1/legal/privacy"},
        {"title": "Terms of Service", "slug": "terms", "url": "/v1/legal/terms"},
        {"title": "Refund Policy", "slug": "refund", "url": "/v1/legal/refund"},
    ])
