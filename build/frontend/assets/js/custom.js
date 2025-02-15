function dropHandler(ev) {
    console.log("File(s) dropped");

  // Prevent default behavior (Prevent file from being opened)
    ev.preventDefault();

    inputFile = document.getElementById("inputFile");
    fileName = document.getElementById("fileName");

    const files = [];

    if (ev.dataTransfer.items) {
      // Use DataTransferItemList interface to access the file(s)
      [...ev.dataTransfer.items].forEach((item, i) => {
        // If dropped items aren't files, reject them
        if (item.kind === "file") {
          const file = item.getAsFile();
          if (file.type !== "application/pdf") {
            fileName.value = "Not a pdf file"
            return
          }
          fileName.value = file.name;
          files.push(file);
          console.log(file);

          setFiles(inputFile, files);
        }
      });
    } else {
        // Use DataTransfer interface to access the file(s)
        [...ev.dataTransfer.files].forEach((file, i) => {
          console.log(`… file[${i}].name = ${file.name}`);
          inputFile.files.add(file)
        });
    }
}

function setFiles(input, files){
  const dataTransfer = new DataTransfer()
  htmx.find('#progress').setAttribute('value', 0);
  for(const file of files)
    dataTransfer.items.add(file)
  input.files = dataTransfer.files
}

function dragOverHandler(ev) {
  console.log("File(s) in drop zone");
  ev.dataTransfer = new DataTransfer();

  // Prevent default behavior (Prevent file from being opened)
  ev.preventDefault();
}




htmx.on('#form', 'htmx:xhr:progress', function(evt) {
    htmx.find('#progress').setAttribute('value', evt.detail.loaded/evt.detail.total * 100)
  });