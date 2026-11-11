(function () {
  var STATUSES = ['todo','doing','review','done'];
  var tokenEl = document.querySelector('meta[name="csrf-token"]');
  var token = tokenEl ? tokenEl.content : '';
  var dragId = null;
  var drawer = document.getElementById('task-drawer');
  var backdrop = document.getElementById('task-backdrop');

  function move(id, status) {
    fetch('/tasks/' + id + '/move', {method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token},body:JSON.stringify({status:status})})
      .then(function(r){return r.json().then(function(d){return {ok:r.ok,d:d};});})
      .then(function(res){if(res.ok){location.reload();}else{alert(res.d.error || 'Could not move task.');}})
      .catch(function(){alert('Network error. Try again.');});
  }
  function closeDrawer(){if(drawer){drawer.classList.remove('open');}if(backdrop){backdrop.classList.remove('open');}}
  function openDrawer(card){
    if(!drawer) return;
    document.getElementById('drawer-title').textContent=card.dataset.title||'Task';
    document.getElementById('drawer-status').textContent=card.dataset.status||'—';
    document.getElementById('drawer-priority').textContent=card.dataset.priority||'—';
    document.getElementById('drawer-deadline').textContent=card.dataset.deadline||'—';
    document.getElementById('drawer-assignee').textContent=card.dataset.assigneeName||'Unassigned';
    document.getElementById('drawer-description').textContent=card.dataset.description||'No description added.';
    var edit=document.getElementById('drawer-edit'); edit.href='/tasks/'+card.dataset.id+'/edit';
    drawer.classList.add('open'); backdrop.classList.add('open');
  }
  document.addEventListener('dragstart',function(e){var t=e.target.closest&&e.target.closest('.task');if(t&&t.getAttribute('draggable')==='true'){dragId=t.dataset.id;t.classList.add('dragging');if(e.dataTransfer)e.dataTransfer.setData('text/plain',dragId);}});
  document.addEventListener('dragend',function(){dragId=null;document.querySelectorAll('.dragging,.over').forEach(function(n){n.classList.remove('dragging','over');});});
  document.addEventListener('dragover',function(e){var c=e.target.closest&&e.target.closest('.col');if(c&&dragId){e.preventDefault();c.classList.add('over');}});
  document.addEventListener('dragleave',function(e){var c=e.target.closest&&e.target.closest('.col');if(c&&!c.contains(e.relatedTarget))c.classList.remove('over');});
  document.addEventListener('drop',function(e){var c=e.target.closest&&e.target.closest('.col');if(c&&dragId){e.preventDefault();c.classList.remove('over');move(dragId,c.dataset.status);}});
  document.addEventListener('click',function(e){
    if(e.target.closest('#drawer-close')||e.target===backdrop){closeDrawer();return;}
    var card=e.target.closest&&e.target.closest('.task');if(!card)return;
    var col=card.closest('.col');
    var b=e.target.closest('[data-move]');
    if(b){e.preventDefault();e.stopPropagation();var i=STATUSES.indexOf(col.dataset.status)+parseInt(b.dataset.move,10);if(i>=0&&i<STATUSES.length)move(card.dataset.id,STATUSES[i]);return;}
    if(e.target.closest('[data-toggle-done]')){e.preventDefault();e.stopPropagation();move(card.dataset.id,col.dataset.status==='done'?'todo':'done');return;}
    if(e.target.closest('a,button,form'))return;
    openDrawer(card);
  });
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeDrawer();if((e.key==='Enter'||e.key===' ')&&document.activeElement&&document.activeElement.classList.contains('task')){e.preventDefault();openDrawer(document.activeElement);}});
  if(backdrop)backdrop.addEventListener('click',closeDrawer);
})();
