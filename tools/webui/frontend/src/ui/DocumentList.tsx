import React from "react";
import {useUiStore} from "store/UiStore";
import {observer} from "mobx-react-lite";
import {ChangeDocumentNameFunction, DeleteDocumentFunction, Document, DocumentJson, SendToOutDirFunction} from "ui/Document";
import {useTranslation} from "react-i18next";
import {styled, Table, TableBody, TableCell, TableHead, TableRow} from "@mui/material";
import Title from "ui/Title";


const StyledTableRow = styled(TableRow)(({theme }) => ({
    '&:nth-of-type(odd)': {
        backgroundColor: theme.palette.action.hover,
    },
    // hide last border
    '&:last-child td, &:last-child th': {
        border: 0,
    },
}));

export const DocumentList: React.FC = observer(({}) => {
    const {t} = useTranslation();
    const uiStore = useUiStore();

    const documents = uiStore.documents;
    const changeDocumentName = (i: number) => {
        return ((newName) => uiStore.setDocument(i, {...documents[i], name: newName})) as ChangeDocumentNameFunction;
    };
    const sendToOutDir = (i: number) => {
        return (() => uiStore.moveDocumentToOutDir(i)) as SendToOutDirFunction;
    };
    const deleteDocument = (i: number) => {
        return (() => uiStore.deleteDocument(i)) as DeleteDocumentFunction;
    };

    const documentsTable = <Table size="small">
        <TableHead>
            <TableRow>
                <TableCell>{t("documents.table.url")}</TableCell>
                <TableCell>{t("documents.table.name")}</TableCell>
                <TableCell>{}</TableCell>
            </TableRow>
        </TableHead>
        <TableBody>
        {documents.map((d: DocumentJson, i: number) =>
            <StyledTableRow key={d.name}>
                <Document name={d.name} changeDocumentName={changeDocumentName(i)} sendToOutDir={sendToOutDir(i)}
                          deleteDocument={deleteDocument(i)}
                          url={uiStore.documentUrl(i, false)}
                          downloadUrl={uiStore.documentUrl(i, true)}
                          setPreviewUrl={uiStore.setPDFPreview}
                />
            </StyledTableRow>)}
        </TableBody>
    </Table>;

    return <>
        <Title>{t("documents.titleList")}</Title>
        {documentsTable}
    </>;
});

export const DocumentListOut: React.FC = observer(({}) => {
    const {t} = useTranslation();
    const uiStore = useUiStore();

    const documentsOut = uiStore.documentsOut;

    const documentsOutTable = <Table size="small">
        <TableHead>
            <TableRow>
                <TableCell>{t("documents.table.name")}</TableCell>
                <TableCell></TableCell>
                <TableCell></TableCell>
            </TableRow>
        </TableHead>
        <TableBody>
        {documentsOut.map((d: DocumentJson) =>
            <StyledTableRow key={d.id}>
                <Document name={d.name} />
            </StyledTableRow>)}
        </TableBody>
    </Table>;

    return <>
        <Title>{t("documents.titleOutList")}</Title>
        {documentsOutTable}
    </>
});
