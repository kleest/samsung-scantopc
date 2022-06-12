const express = require("express");
const logger = require("morgan");
const dotenv = require("dotenv");

dotenv.config();

const documentsRouter = require("./routes/documents");

const app = express();

app.use(logger("dev"));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.use(express.static(process.env.STATIC_DIR));
app.use("/api/documents", documentsRouter);

module.exports = app;
