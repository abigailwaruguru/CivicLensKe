// portal.js: Donation portal for logged-in users

// Redirect to login if not logged in
const username = localStorage.getItem('civiclens_loggedin');
if (!username) {
  window.location.href = 'login.html';
}

document.getElementById('welcome-section').innerHTML = `<h3>Welcome, ${username}!</h3>`;

document.getElementById('logout-btn').onclick = function() {
  localStorage.removeItem('civiclens_loggedin');
  window.location.href = 'login.html';
};

// Load transactions from localStorage
function getTransactions() {
  return JSON.parse(localStorage.getItem('civiclens_transactions') || '[]');
}
function saveTransactions(transactions) {
  localStorage.setItem('civiclens_transactions', JSON.stringify(transactions));
}

function getStatusAndReason(amount) {
  if (amount > 10000) return { status: "Violation", reason: "Donation exceeds legal limit" };
  if (amount > 5000) return { status: "Suspicious", reason: "Large amount flagged" };
  return { status: "Compliant", reason: "" };
}

function renderTable() {
  const transactions = getTransactions();
  const tbody = document.querySelector("#transactions-table tbody");
  tbody.innerHTML = "";
  transactions.forEach(tx => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${tx.donor}</td>
      <td>${tx.candidate}</td>
      <td>${tx.amount}</td>
      <td>${tx.paymentMethod}</td>
      <td>${tx.timestamp}</td>
      <td class="status-${tx.status}">${tx.status}</td>
      <td>${tx.reason}</td>
    `;
    tbody.appendChild(tr);
  });
}

document.getElementById("donation-form").addEventListener("submit", function(e) {
  e.preventDefault();
  const form = e.target;
  const donor = form.donor.value.trim();
  const candidate = form.candidate.value.trim();
  const amount = Number(form.amount.value);
  const paymentMethod = form.paymentMethod.value.trim();
  const timestamp = new Date().toISOString().replace("T", " ").slice(0, 19);

  const { status, reason } = getStatusAndReason(amount);

  const transactions = getTransactions();
  const newTx = {
    id: transactions.length + 1,
    donor, candidate, amount, paymentMethod, timestamp, status, reason
  };
  transactions.unshift(newTx);
  saveTransactions(transactions);
  renderTable();
  form.reset();
});

function downloadReport(format) {
  const transactions = getTransactions();
  let data, filename;
  if (format === "csv") {
    const header = "Donor,Candidate,Amount,PaymentMethod,Timestamp,Status,Reason\n";
    const rows = transactions.map(tx =>
      [tx.donor, tx.candidate, tx.amount, tx.paymentMethod, tx.timestamp, tx.status, tx.reason].join(",")
    );
    data = header + rows.join("\n");
    filename = "regulator_alert_pack.csv";
  } else {
    data = JSON.stringify(transactions, null, 2);
    filename = "regulator_alert_pack.json";
  }
  const blob = new Blob([data], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

document.getElementById("download-csv").addEventListener("click", () => downloadReport("csv"));
document.getElementById("download-json").addEventListener("click", () => downloadReport("json"));

// Initial render
renderTable();
