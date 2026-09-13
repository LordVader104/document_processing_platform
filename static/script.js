function highlightText(text, query) {
    const words = query.trim().split(/\s+/);

    let highlightedText = text;

    for (const word of words) {
        if (!word) continue;

        const escapedWord = word.replace(
            /[.*+?^${}()|[\]\\]/g,
            "\\$&"
        );

        const regex = new RegExp(
            `(${escapedWord})`,
            "gi"
        );

        highlightedText = highlightedText.replace(
            regex,
            "<mark>$1</mark>"
        );
    }

    return highlightedText;
}


/* =========================
   SEARCH
   ========================= */

async function search(page = 1) {

    const query =
        document.getElementById("searchInput").value.trim();

    const resultsContainer =
        document.getElementById("results");

    const algorithm =
        document.getElementById("algorithmSelect").value;


    if (!query) {

        resultsContainer.innerHTML =
            "<p>Please enter a search query.</p>";

        return;
    }


    resultsContainer.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <span>Searching...</span>
        </div>
    `;


    try {

        const response = await fetch(
            `/search?q=${encodeURIComponent(query)}&algorithm=${algorithm}`
        );


        if (!response.ok) {
            throw new Error("Search request failed.");
        }


        const data =
            await response.json();

        const results =
            data.results;


        if (results.length === 0) {

            resultsContainer.innerHTML =
                `<p>No results found for "<strong>${query}</strong>".</p>`;

            return;
        }


        resultsContainer.innerHTML = `
            <p class="result-count">
                Found in ${data.total_results} page(s)
                — Ranking: ${data.algorithm.toUpperCase()}
            </p>
        `;


        for (const result of results) {

            const resultElement =
                document.createElement("div");

            resultElement.className =
                "result";


            resultElement.innerHTML = `
                <h3>
                    ${result.document}

                    ${
                        result.page
                            ? `<span>— Page ${result.page}</span>`
                            : ""
                    }
                </h3>

                <div class="score">
                    Score: ${result.score.toFixed(4)}
                </div>

                <p>
                    ${highlightText(
                        result.snippet,
                        query
                    )}
                </p>
            `;


            resultsContainer.appendChild(
                resultElement
            );
        }


        const pagination =
            document.createElement("div");

        pagination.className =
            "pagination";


        if (page > 1) {

            const previousButton =
                document.createElement("button");

            previousButton.textContent =
                "Previous";

            previousButton.onclick =
                () => search(page - 1);

            pagination.appendChild(
                previousButton
            );
        }


        if (
            page * data.limit <
            data.total_results
        ) {

            const nextButton =
                document.createElement("button");

            nextButton.textContent =
                "Next";

            nextButton.onclick =
                () => search(page + 1);

            pagination.appendChild(
                nextButton
            );
        }


        resultsContainer.appendChild(
            pagination
        );


    } catch (error) {

        console.error(error);

        resultsContainer.innerHTML =
            "<p>Something went wrong while searching.</p>";
    }
}


/* Enter = Search */

document
    .getElementById("searchInput")
    .addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {
                search();
            }

        }
    );


/* =========================
   UPLOAD
   ========================= */

const uploadArea =
    document.getElementById("uploadArea");

const fileInput =
    document.getElementById("fileInput");

const uploadStatus =
    document.getElementById("uploadStatus");


/* Click upload area */

uploadArea.addEventListener(
    "click",
    function () {

        fileInput.click();

    }
);


/* File selected */

fileInput.addEventListener(
    "change",
    function () {

        uploadFiles(fileInput.files);

    }
);


/* Drag over */

uploadArea.addEventListener(
    "dragover",
    function (event) {

        event.preventDefault();

        uploadArea.classList.add(
            "dragover"
        );

    }
);


/* Drag leave */

uploadArea.addEventListener(
    "dragleave",
    function () {

        uploadArea.classList.remove(
            "dragover"
        );

    }
);


/* Drop */

uploadArea.addEventListener(
    "drop",
    function (event) {

        event.preventDefault();

        uploadArea.classList.remove(
            "dragover"
        );

        uploadFiles(
            event.dataTransfer.files
        );

    }
);


/* Upload files */

async function uploadFiles(files) {

    if (!files || files.length === 0) {
        return;
    }


    uploadStatus.innerHTML = "";


    for (const file of files) {

        const uploadItem =
            document.createElement("div");


        uploadItem.className =
            "upload-item";


        uploadItem.innerHTML = `
            <div class="loading">

                <div class="spinner"></div>

                <span>
                    ${file.name} — Uploading and indexing...
                </span>

            </div>
        `;


        uploadStatus.appendChild(
            uploadItem
        );


        const formData =
            new FormData();


        formData.append(
            "file",
            file
        );


        try {

            const response =
                await fetch(
                    "/documents/upload",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Upload failed."
                );
            }


            uploadItem.className =
                "upload-item upload-success";


            uploadItem.textContent =
                `${file.name} — ✓ Indexed`;


            await loadDocumentList();


        } catch (error) {

            console.error(error);


            uploadItem.className =
                "upload-item upload-error";


            uploadItem.textContent =
                `${file.name} — ✕ ${error.message}`;
        }
    }
}


/* =========================
   DOCUMENT LIST
   ========================= */

async function loadDocumentList() {

    const documentList =
        document.getElementById("documentList");

    const documentsSection =
        document.getElementById("documentsSection");


    try {

        const response =
            await fetch("/documents");


        if (!response.ok) {

            throw new Error(
                "Could not load documents."
            );
        }


        const data =
            await response.json();


        documentList.innerHTML = "";


        const files =
            data.files;


        if (files.length === 0) {

            documentsSection.classList.remove(
                "has-documents"
            );

            return;
        }


        documentsSection.classList.add(
            "has-documents"
        );


        for (const file of files) {

            const item =
                document.createElement("div");


            item.className =
                "document-item";


            const safeFileName =
                file.filename.replace(
                    /'/g,
                    "\\'"
                );


            item.innerHTML = `
                <span class="document-name">
                    ${file.filename}
                </span>

                <button
                    class="delete-button"
                    onclick="deleteFile('${safeFileName}')"
                >
                    Delete
                </button>
            `;


            documentList.appendChild(item);
        }


    } catch (error) {

        console.error(error);

        documentsSection.classList.remove(
            "has-documents"
        );

        documentList.innerHTML =
            "<p>Could not load document list.</p>";
    }
}


/* =========================
   DELETE DOCUMENT
   ========================= */

async function deleteFile(fileName) {

    const confirmed =
        confirm(
            `Delete "${fileName}"?`
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/documents/${encodeURIComponent(fileName)}`,
                {
                    method: "DELETE"
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Delete failed."
            );
        }


        await loadDocumentList();


        const uploadItems =
            document.querySelectorAll(
                ".upload-item"
            );


        for (const item of uploadItems) {

            if (
                item.textContent.includes(
                    fileName
                )
            ) {

                item.remove();

                break;
            }
        }


        console.log(
            `${fileName} deleted successfully.`
        );


    } catch (error) {

        console.error(error);


        alert(
            `Could not delete ${fileName}: ${error.message}`
        );
    }
}


/* =========================
   INITIALIZE
   ========================= */

loadDocumentList();

/* =========================
   SYSTEM INFO
   ========================= */

loadSystemInfo();

async function loadSystemInfo() {
    try {
        const response = await fetch("/system-info");

        if (!response.ok) {
            throw new Error("System info request failed");
        }

        const data = await response.json();

        console.log("SYSTEM INFO:", data);

        document.getElementById("systemName").textContent = data.system;
        document.getElementById("cpuInfo").textContent = data.cpu;
        document.getElementById("ramInfo").textContent = data.ram;

        document.getElementById("workerInfo").textContent =
            data.workers;

        document.getElementById("workerNote").textContent =
            `Document processing workers: ${data.workers}`;

    } catch (error) {
        console.error("SYSTEM INFO ERROR:", error);
    }
}