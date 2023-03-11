import React, {useState} from "react";
import {useTranslation} from "react-i18next";
import {IconDeviceFloppy, IconEye, IconSend} from "@tabler/icons-react";

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
        <td><a target="_blank" href={downloadUrl && downloadUrl}>{name}</a></td>
        <td><span>{changeDocumentName &&
            <input type="text" value={nameValue} onChange={(e) => setNameValue(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && changeDocumentName(nameValue)}/>
        }</span></td>
        <td>
            <span>
                {changeDocumentName && <button onClick={(e) => changeDocumentName(nameValue)} disabled={nameValue === name} title={t("documents.buttonSave")}>
                <IconDeviceFloppy />
                </button>}
                {sendToOutDir && <button onClick={(e) => sendToOutDir()} disabled={nameValue !== name} title={t("documents.buttonSendToOutDir")}>
                    <IconSend />
                </button>}
                {setPreviewUrl && url && name.endsWith(".pdf") &&
                    <button onClick={(e) => setPreviewUrl(url)} title={t("documents.buttonPreview")}><IconEye /></button>
                }
            </span>
        </td>
    </>;
};
