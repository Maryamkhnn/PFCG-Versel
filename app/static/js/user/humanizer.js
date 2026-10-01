console.log("Humanizer JS Loaded");
/*=========================================
PFCG AI HUMANIZER
=========================================*/

// Elements
const aiContent = document.getElementById("aiContent");
const humanizedContent = document.getElementById("humanizedContent");

const humanizeBtn = document.getElementById("humanizeBtn");
const copyBtn = document.getElementById("copyBtn");
const saveBtn = document.getElementById("saveBtn");
const downloadBtn = document.getElementById("downloadBtn");

const inputWords = document.getElementById("inputWords");
const outputWords = document.getElementById("outputWords");


// ===============================
// Word Counter
// ===============================

function countWords(text){

    if(!text.trim()) return 0;

    return text.trim().split(/\s+/).length;

}

if(aiContent){

    aiContent.addEventListener("input",()=>{

        inputWords.innerHTML =
        countWords(aiContent.value) + " Words";

    });

}


// ===============================
// Humanize
// ===============================

if(humanizeBtn){

humanizeBtn.addEventListener("click", async ()=>{

    if(aiContent.value.trim()===""){

        showToast(
            "Paste AI content first.",
            "warning"
        );

        return;

    }

    humanizeBtn.disabled=true;

    humanizeBtn.innerHTML=
    '<i class="fas fa-spinner fa-spin"></i> Humanizing...';

    try{

        const response = await fetch("/humanize",{

            method:"POST",

            headers:{
                "Content-Type":"application/json"
            },

            body:JSON.stringify({

                content:aiContent.value

            })

        });

        const data = await response.json();

        if(data.success){

            humanizedContent.value = data.content;

            outputWords.innerHTML =
            data.word_count + " Words";

            showToast(
                "Content Humanized Successfully.",
                "success"
            );

        }

        else{

            showToast(
                data.message,
                "error"
            );

        }

    }

    catch(error){

        console.log(error);

        showToast(
            "Server Error",
            "error"
        );

    }

    finally{

        humanizeBtn.disabled=false;

        humanizeBtn.innerHTML=
        '<i class="fas fa-user-pen"></i> Humanize';

    }

});

}


// ===============================
// Copy
// ===============================

if(copyBtn){

copyBtn.addEventListener("click",()=>{

    if(humanizedContent.value===""){

        showToast(
            "Nothing to copy.",
            "warning"
        );

        return;

    }

    navigator.clipboard.writeText(

        humanizedContent.value

    );

    showToast(
        "Copied Successfully.",
        "success"
    );

});

}


// ===============================
// Download
// ===============================

if(downloadBtn){

downloadBtn.addEventListener("click",()=>{

    if(humanizedContent.value===""){

        showToast(
            "Nothing to export.",
            "warning"
        );

        return;

    }

    const blob = new Blob(

        [humanizedContent.value],

        {type:"text/plain"}

    );

    const link=document.createElement("a");

    link.href=URL.createObjectURL(blob);

    link.download="Humanized_Content.txt";

    link.click();

});

}


// ===============================
// Save
// ===============================

if(saveBtn){

saveBtn.addEventListener("click",()=>{

    showToast(
        "Save API will connect next.",
        "info"
    );

});

}