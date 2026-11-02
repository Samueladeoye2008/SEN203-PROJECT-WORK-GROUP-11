// Kanban interaction: drag-and-drop, arrow buttons and the done circle call POST /tasks/<id>/move.
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
    if (c && !c.contains(e.relatedTarget)) { c.classList.remove("over"); }
  });
  document.addEventListener("drop", function (e) {
    var c = e.target.closest && e.target.closest(".col");
    if (c && dragId) { e.preventDefault(); move(dragId, c.dataset.status); }
  });

  document.addEventListener("click", function (e) {
    var card = e.target.closest && e.target.closest(".task");
    if (!card) { return; }
    var col = card.closest(".col");
    var b = e.target.closest("[data-move]");
    if (b) {
      var i = STATUSES.indexOf(col.dataset.status) + parseInt(b.dataset.move, 10);
      if (i >= 0 && i < STATUSES.length) { move(card.dataset.id, STATUSES[i]); }
      return;
    }
    if (e.target.closest("[data-toggle-done]")) {
      move(card.dataset.id, col.dataset.status === "done" ? "todo" : "done");
    }
  });
})();
