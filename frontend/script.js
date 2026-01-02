// ---------------- LOGIN ----------------
function login() {
  const user = document.getElementById("username").value;
  if (!user) return alert("Enter username");
  localStorage.setItem("user_id", user);
  window.location.href = "home.html";
}

// ---------------- NAVIGATION ----------------
function navigate(page) {
  const user = localStorage.getItem("user_id");
  if (!user && page !== 'index') return alert("Please login first");
  
  switch(page) {
    case 'home': window.location.href = "home.html"; break;
    case 'buy': window.location.href = "buy.html"; break;
    case 'sell': window.location.href = "sell.html"; break;
    case 'profile': window.location.href = "profile.html"; break;
  }
}

// ---------------- BUY SUGGESTIONS ----------------
function getBuySuggestions() {
  const amount = document.getElementById("amount").value;
  if (!amount) return alert("Enter amount");

  fetch("http://127.0.0.1:5000/buy-suggestions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount: amount })
  })
  .then(res => res.json())
  .then(data => {
    let html = "";
    if (data.error) {
      html = `<p>Error: ${data.error}</p>`;
    } else if (data.length === 0) {
      html = "<p>No stocks available for this amount</p>";
    } else {
      data.forEach(stock => {
        html += `
          <p>${stock.symbol} - ₹${stock.price}
          <button onclick="buyStock('${stock.symbol}', ${stock.price})">Buy</button></p>`;
      });
    }
    document.getElementById("suggestions").innerHTML = html;
  });
}

// ---------------- BUY STOCK ----------------
function buyStock(symbol, price) {
  fetch("http://127.0.0.1:5000/buy-stock", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: localStorage.getItem("user_id"),
      symbol: symbol,
      price: price,
      quantity: 1
    })
  })
  .then(res => res.json())
  .then(data => alert(data.message));
}

// ---------------- PORTFOLIO DISPLAY ----------------
function loadPortfolio(divId) {
  const user_id = localStorage.getItem("user_id");
  fetch(`http://127.0.0.1:5000/portfolio/${user_id}`)
    .then(res => res.json())
    .then(data => {
      let html = "";
      if (data.length === 0) html = "<p>No stocks in your portfolio</p>";
      data.forEach(stock => {
        html += `<p>${stock.symbol} | Qty: ${stock.quantity} | ₹${stock.price}
          <button onclick="sellStock('${stock.symbol}')">Sell</button></p>`;
      });
      document.getElementById(divId).innerHTML = html;
    });
}

// ---------------- SELL STOCK ----------------
function sellStock(symbol) {
  fetch("http://127.0.0.1:5000/sell-stock", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: localStorage.getItem("user_id"),
      symbol: symbol
    })
  })
  .then(res => res.json())
  .then(data => alert(data.message))
  .then(() => window.location.reload());
}

// ---------------- PAGE LOAD ----------------
window.onload = function() {
  const path = window.location.pathname;
  if (path.includes("home.html")) {
    document.getElementById("user").innerText = localStorage.getItem("user_id");
  }
  if (path.includes("sell.html")) loadPortfolio("portfolio");
  if (path.includes("profile.html")) loadPortfolio("portfolio");
};
