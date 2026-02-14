const stetho = document.querySelector(".stetho");

document.addEventListener("mousemove", (e) => {
  const x = (window.innerWidth / 2 - e.clientX) / 30;
  const y = (window.innerHeight / 2 - e.clientY) / 30;

  stetho.style.transform = `translate(${x}px, ${y}px)`;
});
