const nav=document.getElementById('nav'),burger=document.getElementById('burger'),menu=document.getElementById('menu');
addEventListener('scroll',()=>nav.classList.toggle('small',scrollY>40),{passive:true});
burger.onclick=()=>{burger.classList.toggle('open');menu.classList.toggle('open')};
menu.querySelectorAll('a').forEach(a=>a.onclick=()=>{burger.classList.remove('open');menu.classList.remove('open')});

// Hiện dần khi cuộn
const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target)}}),{threshold:.12});
document.querySelectorAll('.reveal').forEach((el,i)=>{el.style.transitionDelay=(i%3)*.12+'s';io.observe(el)});

// Chữ hero trôi nhẹ khi cuộn
const heroIn=document.querySelector('.hero-in');
addEventListener('scroll',()=>{const y=Math.min(scrollY,700);heroIn.style.transform=`translateY(${y*.25}px)`;heroIn.style.opacity=1-y/800},{passive:true});

// Ảnh nghiêng nhẹ theo chuột
document.querySelectorAll('.spot .img').forEach(el=>{
  el.addEventListener('mousemove',e=>{const r=el.getBoundingClientRect();
    el.firstElementChild.style.transformOrigin=`${(e.clientX-r.left)/r.width*100}% ${(e.clientY-r.top)/r.height*100}%`});
});

// Xem thêm
document.querySelectorAll('.more').forEach(a=>a.onclick=e=>{
  e.preventDefault();const s=a.closest('.spot');s.classList.toggle('open');
  a.textContent=s.classList.contains('open')?'Thu gọn':'Xem thêm';
});