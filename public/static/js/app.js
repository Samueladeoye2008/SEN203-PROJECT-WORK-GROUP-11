(function(){
  function $(s){return document.querySelector(s)}
  function toggleTheme(){var dark=document.documentElement.classList.toggle('dark');try{localStorage.setItem('theme',dark?'dark':'light')}catch(e){}}
  var theme=$('#theme-toggle');if(theme)theme.addEventListener('click',toggleTheme);
  var mobile=$('#mobile-menu'), sidebar=$('#sidebar');if(mobile&&sidebar){mobile.addEventListener('click',function(){sidebar.style.display=sidebar.style.display==='flex'?'none':'flex';sidebar.style.width='270px';sidebar.style.boxShadow='20px 0 50px rgba(0,0,0,.16)';});}
  document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('[data-toggle]');if(t){var el=$(t.dataset.toggle);if(el){e.preventDefault();el.classList.toggle('hide');if(!el.classList.contains('hide')){var f=el.querySelector('input:not([type=hidden]),select,textarea');if(f)f.focus()}}return}var c=e.target.closest&&e.target.closest('[data-copy]');if(c&&navigator.clipboard){var old=c.innerHTML;navigator.clipboard.writeText(c.dataset.copy).then(function(){c.textContent='Copied!';setTimeout(function(){c.innerHTML=old},1200)})}});
  var search=$('#search'),mine=$('#mine-toggle'),mineOn=false;
  function filter(){var q=search?search.value.trim().toLowerCase():'';document.querySelectorAll('[data-search]').forEach(function(el){var hide=q!==''&&el.dataset.search.indexOf(q)===-1;if(el.classList.contains('task')&&mineOn&&mine&&el.dataset.assignee!==mine.dataset.me)hide=true;el.classList.toggle('hide',hide)})}
  if(search)search.addEventListener('input',filter);if(mine)mine.addEventListener('click',function(){mineOn=!mineOn;mine.classList.toggle('primary',mineOn);filter()});
})();
