import { expect, test } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Define the prohibited phrases for medical overclaim audit
const PROHIBITED_PHRASES = [
  '診斷',
  '確診',
  '治療',
  '治癒',
  '一定',
  '絕對',
  '保證',
  '100%',
  '取代醫師',
  '正常代表沒問題',
  'diagnose',
  'guarantee',
  'cure',
];

function assertNoProhibitedPhrases(text: string) {
  // Exclude the standard disclaimers
  const cleanedText = text
    .replace(/不構成醫療診斷/g, '')
    .replace(/非醫療診斷/g, '')
    .replace(/醫療診斷/g, '')
    .replace(/診斷建議/g, '');
  for (const phrase of PROHIBITED_PHRASES) {
    expect(cleanedText.toLowerCase()).not.toContain(phrase.toLowerCase());
  }
}

// Function to generate a minimal valid PDF with specified lines
function makeMinimalPdf(textLines: string[]): Buffer {
  let streamContent = "BT\n/F1 12 Tf\n14 TL\n72 712 Td\n";
  for (const line of textLines) {
    const escaped = line.replace(/\(/g, "\\(").replace(/\)/g, "\\)");
    streamContent += `(${escaped}) Tj\nT*\n`;
  }
  streamContent += "ET\n";

  const streamBytes = Buffer.from(streamContent, "latin1");
  const streamLen = streamBytes.length;

  const objects: Buffer[] = [
    Buffer.from("1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n", "latin1"),
    Buffer.from("2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n", "latin1"),
    Buffer.from("3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n", "latin1"),
    Buffer.from("4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n", "latin1"),
    Buffer.concat([
      Buffer.from(`5 0 obj\n<< /Length ${streamLen} >>\nstream\n`, "latin1"),
      streamBytes,
      Buffer.from("\nendstream\nendobj\n", "latin1")
    ])
  ];

  let pdfBytes = Buffer.from("%PDF-1.4\n", "latin1");
  const offsets: number[] = [];
  for (const obj of objects) {
    offsets.push(pdfBytes.length);
    pdfBytes = Buffer.concat([pdfBytes, obj]);
  }

  const xrefOffset = pdfBytes.length;
  let xref = `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets) {
    xref += `${String(offset).padStart(10, '0')} 00000 n \n`;
  }
  
  pdfBytes = Buffer.concat([
    pdfBytes,
    Buffer.from(xref, "latin1"),
    Buffer.from(`trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`, "latin1")
  ]);

  return pdfBytes;
}

test.describe('P158 — Live Product Flow Smoke Harness', () => {
  // Gate the entire suite behind the environment flag
  const runLive = process.env.RUN_LIVE_PRODUCT_FLOW_SMOKE === '1';

  test.skip(!runLive, 'Skipping live smoke test by default. Set RUN_LIVE_PRODUCT_FLOW_SMOKE=1 to run.');

  let credentials: any;

  test.beforeAll(async ({ request }) => {
    if (!runLive) return;

    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000';
    const email = `smoke-p158-${Math.random().toString(36).substring(2, 10)}@example.com`;
    const password = 'Password123!';

    try {
      // 1. Register User
      const registerResp = await request.post(`${backendUrl}/api/v1/auth/register`, {
        data: { email, password },
      });
      if (!registerResp.ok()) {
        throw new Error(`Register failed: Status ${registerResp.status()} - ${await registerResp.text()}`);
      }

      // 2. Login User
      const loginResp = await request.post(`${backendUrl}/api/v1/auth/login`, {
        data: { email, password },
      });
      if (!loginResp.ok()) {
        throw new Error(`Login failed: Status ${loginResp.status()} - ${await loginResp.text()}`);
      }
      const loginJson = await loginResp.json();
      const token = loginJson.access_token;

      // 3. Get Person Profile
      const personsResp = await request.get(`${backendUrl}/api/v1/persons`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!personsResp.ok()) {
        throw new Error(`Get persons failed: Status ${personsResp.status()} - ${await personsResp.text()}`);
      }
      const personsJson = await personsResp.json();
      const selfPerson = personsJson.find((p: any) => p.relationship === 'self');
      if (!selfPerson) {
        throw new Error('Self person profile not found in registration response.');
      }
      const personId = selfPerson.id;

      // 4. Generate Synthetic Lab Report
      const syntheticLines = [
        "Glucose: 110 mg/dL",
        "AST: 45 U/L",
        "ALT: 50 U/L",
        "Total Cholesterol: 240 mg/dL",
      ];
      const pdfBytes = makeMinimalPdf(syntheticLines);

      // 5. Upload Document
      const uploadResp = await request.post(`${backendUrl}/api/v1/documents/upload?person_id=${personId}`, {
        headers: { Authorization: `Bearer ${token}` },
        multipart: {
          category: 'health_check',
          file: {
            name: 'synthetic_report.pdf',
            mimeType: 'application/pdf',
            buffer: pdfBytes,
          },
        },
      });
      if (!uploadResp.ok()) {
        throw new Error(`Upload document failed: Status ${uploadResp.status()} - ${await uploadResp.text()}`);
      }
      const uploadJson = await uploadResp.json();
      const documentId = uploadJson.id;

      // 6. Trigger Parse
      const parseResp = await request.post(`${backendUrl}/api/v1/documents/${documentId}/parse?person_id=${personId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!parseResp.ok()) {
        throw new Error(`Parse failed: Status ${parseResp.status()} - ${await parseResp.text()}`);
      }

      // 7. Confirm Document
      const confirmPayload = {
        confirmed_data: {
          reviewed: true,
          items: [
            { item_name: "Glucose", value: 110, unit: "mg/dL" },
            { item_name: "AST", value: 45, unit: "U/L" },
            { item_name: "ALT", value: 50, unit: "U/L" },
            { item_name: "Total Cholesterol", value: 240, unit: "mg/dL" },
          ],
        },
        report_date: new Date().toISOString().split('T')[0],
      };
      const confirmResp = await request.put(`${backendUrl}/api/v1/documents/${documentId}/confirm?person_id=${personId}`, {
        headers: { Authorization: `Bearer ${token}` },
        data: confirmPayload,
      });
      if (!confirmResp.ok()) {
        throw new Error(`Confirm failed: Status ${confirmResp.status()} - ${await confirmResp.text()}`);
      }

      credentials = { email, token, person_id: personId };
    } catch (error: any) {
      console.error(error);
      throw new Error(`Local backend environment issue: ${error.message}. Please ensure local backend is running at http://127.0.0.1:8000 with disposable test database.`);
    }
  });

  test('Dashboard and Actions integration flow validation', async ({ page }) => {
    // 1. Visit root page and inject credentials to localStorage using addInitScript
    await page.addInitScript((creds) => {
      localStorage.setItem('token', creds.token);
      localStorage.setItem('person_id', creds.person_id);
      localStorage.setItem('onboarding_completed', '1');
    }, credentials);

    // Navigate to dashboard
    await page.goto('/platform/dashboard');
    await page.waitForSelector('[data-testid="first-run-journey-card"]', { timeout: 20000 });

    // Assert that active risk signals from the confirmed document are displayed
    await expect(page.getByText('AST 偏高', { exact: true }).first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('總膽固醇偏高', { exact: true }).first()).toBeVisible({ timeout: 10000 });

    // Assert that the narrative card is successfully rendered
    await expect(page.getByText('你的健康正在發生什麼').first()).toBeVisible({ timeout: 10000 });

    // Ensure no ErrorBoundary crash is present on the page
    const dashboardBody = await page.locator('body').innerText();
    expect(dashboardBody).not.toContain('Something went wrong');

    // Run medical claim audit on Dashboard
    assertNoProhibitedPhrases(dashboardBody);

    // Save screenshot if artifact or evidence path is configured
    const evidenceDir = process.env.P158_EVIDENCE_DIR;
    if (evidenceDir) {
      fs.mkdirSync(path.join(evidenceDir, 'screenshots'), { recursive: true });
      await page.screenshot({ path: path.join(evidenceDir, 'screenshots/dashboard.png') });
    }

    // 2. Navigate to Actions page
    await page.goto('/platform/actions');
    await page.waitForSelector('[data-testid="actions-page"]', { timeout: 20000 });

    // Assert page does not contain ErrorBoundary crash
    const actionsBody = await page.locator('body').innerText();
    expect(actionsBody).not.toContain('Something went wrong');

    // Run medical claim audit on Actions
    assertNoProhibitedPhrases(actionsBody);

    const recSection = page.locator('div.rounded-3xl', { has: page.locator('h3:has-text("系統現在建議你先做")') }).first();
    await expect(recSection).toBeVisible({ timeout: 10000 });

    // Verify presence of at least one recommendation
    await expect(recSection.getByText('AST 偏高').first()).toBeVisible({ timeout: 10000 });
    await expect(recSection.getByText('總膽固醇偏高').first()).toBeVisible({ timeout: 10000 });

    // Verify evidence deep link if present
    const sourceLink = recSection.locator('[data-testid="p89-source-page-link"]').first();
    const isLinkVisible = await sourceLink.isVisible();
    if (isLinkVisible) {
      const href = await sourceLink.getAttribute('href');
      expect(href).toContain('/platform/documents');
    } else {
      console.log('No source link present for the current recommendations (likely risk_alert sourceType). Skipping link assertion.');
    }

    if (evidenceDir) {
      await page.screenshot({ path: path.join(evidenceDir, 'screenshots/actions_pre_snooze.png') });
    }

    // 3. Snooze interaction verification
    const cardToSnooze = recSection.locator('div.rounded-2xl.border.p-4').filter({ hasText: '總膽固醇偏高' }).first();
    const snoozeBtn = cardToSnooze.getByRole('button', { name: '稍後提醒' });
    await expect(snoozeBtn).toBeVisible();

    const snoozeRequestPromise = page.waitForRequest(
      (req) => req.url().includes('/actions') && req.method() === 'POST'
    );
    await snoozeBtn.click();

    const snoozeRequest = await snoozeRequestPromise;
    const snoozePayload = JSON.parse(snoozeRequest.postData() || '{}');
    expect(snoozePayload.status).toBe('snoozed');
    expect(snoozePayload.snoozed_until).toBeDefined();

    // Verify that the card is dynamically removed
    await expect(recSection.getByText('總膽固醇偏高')).not.toBeVisible();

    if (evidenceDir) {
      await page.screenshot({ path: path.join(evidenceDir, 'screenshots/actions_post_snooze.png') });
    }
  });
});
