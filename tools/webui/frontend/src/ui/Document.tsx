import React, {useState} from "react";
import {useTranslation} from "react-i18next";
import SaveIcon from "@mui/icons-material/Save";
import DriveFileMoveIcon from "@mui/icons-material/DriveFileMove";
import DeleteIcon from "@mui/icons-material/Delete";
import PreviewIcon from "@mui/icons-material/Preview";
import {IconButton, Input, Link, TableCell, TextField} from "@mui/material";
import {ConfirmationDialog} from "ui/ReusableComponents";

export type DocumentJson = {
    name: string,
    id: string,
};

export type ChangeDocumentNameFunction = (newName: string) => void;
export type SetPreviewUrlFunction = (url: string) => void;
export type SendToOutDirFunction = () => void;
export type DeleteDocumentFunction = () => void;

type Props = {
    name: string,
    url?: string,
    downloadUrl?: string,
    changeDocumentName?: ChangeDocumentNameFunction,
    sendToOutDir?: SendToOutDirFunction,
    deleteDocument?: DeleteDocumentFunction,
    setPreviewUrl?: SetPreviewUrlFunction,
};

export const Document: React.FC<Props> = ({name, url, downloadUrl, changeDocumentName, sendToOutDir, deleteDocument, setPreviewUrl}) => {
    const {t} = useTranslation();
    const [nameValue, setNameValue] = useState(name);
    const [confirmOpen, setConfirmOpen] = useState(false);

    return <>
        <TableCell>{downloadUrl ? <Link target="_blank" rel="noopener" href={downloadUrl}>{name}</Link> : <>{name}</>}</TableCell>
        <TableCell>{changeDocumentName &&
            <TextField fullWidth={true} variant="standard" size="small" value={nameValue} onChange={(e) => setNameValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && changeDocumentName(nameValue)}/>
        }</TableCell>
        <TableCell>
            {changeDocumentName && <IconButton onClick={(e) => changeDocumentName(nameValue)} disabled={nameValue === name} title={t("documents.buttonSave")}>
                <SaveIcon />
            </IconButton>}
            {sendToOutDir && <IconButton onClick={(e) => sendToOutDir()} disabled={nameValue !== name} title={t("documents.buttonSendToOutDir")}>
                <DriveFileMoveIcon />
            </IconButton>}
            {deleteDocument && <IconButton onClick={(e) => setConfirmOpen(true)} disabled={nameValue !== name} title={t("documents.buttonDelete")}>
                <DeleteIcon />
            </IconButton>}
            {setPreviewUrl && url && name.endsWith(".pdf") &&
                <IconButton onClick={(e) => setPreviewUrl(url)} title={t("documents.buttonPreview")}><PreviewIcon /></IconButton>
            }
            {deleteDocument && <ConfirmationDialog titleText={t("dialog.confirmDeletion.title")}
                                                   contentText={t("dialog.confirmDeletion.contentText", {name})}
                                                   open={confirmOpen} onConfirm={deleteDocument} onCancel={() => setConfirmOpen(false)}/>}
        </TableCell>
    </>;
};
