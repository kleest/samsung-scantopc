const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

const express = require("express");
const router = express.Router();

function documentDir() {
    return path.resolve(process.env.DOCUMENT_DIR);
}

function documentOutDir() {
    return path.resolve(process.env.DOCUMENT_OUTPUT_DIR);
}

function documentPath(name) {
    return path.join(documentDir(), name);
}

function documentOutPath(name) {
    return path.join(documentOutDir(), name);
}

function documentId(path) {
    return crypto.createHash("sha512").update(path).digest("hex");
}

function readDocumentDir(cb) {
    return fs.readdir(documentDir(), {withFileTypes: true}, cb);
}

function findDocumentById(id, res, cb) {
    readDocumentDir((err, files) => {
        if (err)
            return res.status(500).json(err);

        const found = files.filter((ent) => ent.isFile() && documentId(documentPath(ent.name)) === id);
        if (found.length === 0)
            return res.status(200).json(false);

        for (let ent of found)
            cb(ent);
    });
}

function fileExists(path) {
    return fs.existsSync(path);
}

/**
 * Lists documents in the document directory
 */
router.get("/list", (req, res) => {
    fs.readdir(documentDir(), {withFileTypes: true}, (err, files) => {
        if (err)
            return res.status(500).json(err);

        const result = [];
        for (let ent of files) {
            if (ent.isFile()) {
                result.push({
                    "name": ent.name,
                    "id": documentId(documentPath(ent.name)),
                });
            }
        }
        res.json(result);
    });
});

/**
 * Lists documents in the document output directory
 */
router.get("/list_outdir", (req, res) => {
    fs.readdir(documentOutDir(), {withFileTypes: true}, (err, files) => {
        if (err)
            return res.status(500).json(err);

        const result = [];
        for (let ent of files) {
            if (ent.isFile()) {
                result.push({
                    "name": ent.name,
                    "id": null,
                });
            }
        }
        res.json(result);
    });
});

/**
 * Returns a document as binary stream.
 */
router.get("/:id", (req, res) => {
    const id = req.params.id;
    findDocumentById(id, res, (ent) => {
        res.sendFile(documentPath(ent.name));
    });
});

/**
 * Returns a document as binary stream for download. Sets appropriate download headers.
 */
router.get("/:id/download", (req, res) => {
    const id = req.params.id;
    findDocumentById(id, res, (ent) => {
        res.download(documentPath(ent.name), ent.name);
    });
});

function _rename_helper(oldPath, newPath, res) {
    if (fileExists(newPath))
        return res.status(500).send("Target file already exists");
    fs.rename(oldPath, newPath, (err) => {
        if (err)
            return res.status(500).json(err);

        res.json(true);
    });
}

/**
 * Changes document properties. Currently, only supports renaming the document.
 */
router.post("/:id", (req, res) => {
    const id = req.params.id;
    const newData = req.body;
    findDocumentById(id, res, (ent) => {
        _rename_helper(documentPath(ent.name), documentPath(path.basename(newData.name)), res)
    });
});

/**
 * Moves a document to the document output directory without changing its name.
 */
router.post("/:id/move_to_outdir", (req, res) => {
    const id = req.params.id;
    findDocumentById(id, res, (ent) => {
        _rename_helper(documentPath(ent.name), documentOutPath(path.basename(ent.name)), res)
    });
});

module.exports = router;
