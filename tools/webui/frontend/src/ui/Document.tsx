import React, {useState} from "react";
import {useTranslation} from "react-i18next";
import SaveIcon from "@mui/icons-material/Save";
import DriveFileMoveIcon from "@mui/icons-material/DriveFileMove";
import PreviewIcon from "@mui/icons-material/Preview";
import {IconButton, Input, Link, TableCell, TextField} from "@mui/material";

export type DocumentJson = {
    name: string,
    id: string,
};

export type ChangeDocumentNameFunction = (newName: string) => void;
export type SetPreviewUrlFunction = (url: string) => void;
export type SendToOutDirFunction = () => void;

type Props = {
    name: string,
    url?: string,
    downloadUrl?: string,
    changeDocumentName?: ChangeDocumentNameFunction,
    sendToOutDir?: SendToOutDirFunction,
    setPreviewUrl?: SetPreviewUrlFunction,
};

export const Document: React.FC<Props> = ({name, url, downloadUrl, changeDocumentName, sendToOutDir, setPreviewUrl}) => {
    const {t} = useTranslation();
    const [nameValue, setNameValue] = useState(name);

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
            {setPreviewUrl && url && name.endsWith(".pdf") &&
                <IconButton onClick={(e) => setPreviewUrl(url)} title={t("documents.buttonPreview")}><PreviewIcon /></IconButton>
            }
        </TableCell>
    </>;
};
