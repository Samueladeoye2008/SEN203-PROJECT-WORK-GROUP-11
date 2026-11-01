// Kanban interaction: drag-and-drop and arrow buttons call POST /tasks/<id>/move.
(function () {
  var STATUSES = ["todo", "doing", "review", "done"];
  var token = document.querySelector('meta[name="csrf-token"]').content;
  var dragId = null;

  function move(id, status) {
    fetch("/tasks/" + id + "/move", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": token },
      body: JSON.stringify({ status: status })
    }).then(function (r) {
      return r.json().then(function (d) { return { ok: r.ok, d: d }; });
    }).then(function (res) {
      if (res.ok) { location.reload(); } else { alert(res.d.error || "Could not move task."); }
    }).catch(function () { alert("Network error. Try again."); });
  }

  document.addEventListener("dragstart", function (e) {
    var t = e.target.closest && e.target.closest(".task");
    if (t) { dragId = t.dataset.id; t.classList.add("dragging"); e.dataTransfer.setData("text/plain", dragId); }
  });
  document.addEventListener("dragend", function () {
    dragId = null;
    document.querySelectorAll(".dragging,.over").forEach(function (n) { n.classList.remove("dragging", "over"); });
  });
  document.addEventListener("dragover", function (e) {
    var c = e.target.closest && e.target.closest(".col");
    if (c && dragId) { e.preventDefault(); c.classList.add("over"); }
  });
  document.addEventListener("dragleave", function (e) {
    var c = e.target.closest && e.target.closest(".col");
    if (c) { c.classList.remove("over"); }
  });
  document.addEventListener("drop", function (e) {
    var c = e.target.closest && e.target.closest(".col");
    if (c && dragId) { e.preventDefault(); move(dragId, c.dataset.status); }
  });
  document.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("[data-move]");
    if (!b) { return; }
    var card = b.closest(".task"), col = b.closest(".col");
    var i = STATUSES.indexOf(col.dataset.status) + parseInt(b.dataset.move, 10);
    if (i >= 0 && i < STATUSES.length) { move(card.dataset.id, STATUSES[i]); }
  });

  // Add-task panel toggle.
  var addBtn = document.getElementById("add-toggle"), addForm = document.getElementById("add-form");
  if (addBtn && addForm) {
    addBtn.addEventListener("click", function () {
      addForm.classList.toggle("hidden");
      var f = addForm.querySelector("input[name=title]"); if (f) { f.focus(); }
    });
  }

  // "Show only my tasks" filter (client side).
  var mine = document.getElementById("mine-toggle");
  if (mine) {
    mine.addEventListener("click", function () {
      var on = mine.getAttribute("aria-pressed") !== "true";
      mine.setAttribute("aria-pressed", on);
      mine.textContent = on ? "Show all tasks" : "Show only my tasks";
      document.querySelectorAll(".task").forEach(function (t) {
        t.classList.toggle("hidden", on && t.dataset.assignee !== mine.dataset.me);
      });
    });
  }

  // Copy join code.
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      if (navigator.clipboard) {
        navigator.clipboard.writeText(b.dataset.copy).then(function () {
          b.textContent = "Copied"; setTimeout(function () { b.textContent = "Copy"; }, 1500);
        });
      }
    });
  });
})();
