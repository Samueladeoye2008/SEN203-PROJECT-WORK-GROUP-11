/**
 * Email relay for the CSC GRP 11 Task Board.
 * Setup: script.google.com > New project > paste this file.
 * Project Settings > Script properties > add SHARED_SECRET (long random text).
 * Deploy > New deployment > Web app > Execute as: Me, Who has access: Anyone.
 * Copy the Web app URL (ends with /exec) into APPS_SCRIPT_URL.
 * After editing this code, use Deploy > Manage deployments > edit > New version.
 */
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!secret || data.secret !== secret) {
      return reply_({ ok: false, error: 'unauthorized' });
    }
    var to = String(data.to || '');
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(to)) {
      return reply_({ ok: false, error: 'bad address' });
    }
    MailApp.sendEmail({
      to: to,
      subject: String(data.subject || '').slice(0, 150),
      body: String(data.body || '').slice(0, 3000),
      name: 'CSC Group 11 Task Board'
    });
    return reply_({ ok: true });
  } catch (err) {
    return reply_({ ok: false, error: String(err) });
  }
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
