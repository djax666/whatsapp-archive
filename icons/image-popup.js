document.addEventListener("DOMContentLoaded", function(){
    let thumbnails = document.querySelectorAll(".image-popup");
    let popupBackground = document.querySelector("#popup-background");
    let popupTitle = document.querySelector("#popup-title");
    let popupImage = document.querySelector("#popup-image");

    for (let i = 0; i < thumbnails.length; i++) {
        thumbnails[i].addEventListener("click", function(){
            popupBackground.style.display = "block";
            popupTitle.innerHTML = this.alt;
            popupImage.src = this.src;
        })
    }
    popupBackground.addEventListener("click", function(){
        popupBackground.style.display = "none";
    })
    document.addEventListener("keydown", function(e){
        if (e.keyCode == 27) {
            popupBackground.style.display = "none";
        }
    })
})