import React from "react";
import {useUiStore} from "store/UiStore";
import {observer} from "mobx-react-lite";
import {ChangeDocumentNameFunction, Document, DocumentJson, SendToOutDirFunction} from "ui/Document";
import {useTranslation} from "react-i18next";

type Props = {
};

export const DocumentList: React.FC<Props> = observer(({}) => {
    const {t} = useTranslation();
    const uiStore = useUiStore();

    const documents = uiStore.documents;
    const documentsOut = uiStore.documentsOut;
    const changeDocumentName = (i: number) => {
        return ((newName) => uiStore.setDocument(i, {...documents[i], name: newName})) as ChangeDocumentNameFunction;
    };
    const sendToOutDir = (i: number) => {
        return (() => uiStore.moveDocumentToOutDir(i)) as SendToOutDirFunction;
    };

    const documentsTable = <table>
        <thead>
        <tr>
            <th>{t("documents.table.url")}</th>
            <th>{t("documents.table.name")}</th>
            <th>{}</th>
        </tr>
        </thead>
        <tbody>
        {documents.map((d: DocumentJson, i: number) =>
            <tr key={d.name}>
                <Document name={d.name} changeDocumentName={changeDocumentName(i)} sendToOutDir={sendToOutDir(i)}
                          url={uiStore.documentUrl(i, false)}
                          downloadUrl={uiStore.documentUrl(i, true)}
                          setPreviewUrl={uiStore.setPDFPreview}
                />
            </tr>)}
        </tbody>
    </table>;

    const documentsOutTable = <table>
        <thead>
            <tr>
                <th>{t("documents.table.name")}</th>
                <th></th>
                <th></th>
            </tr>
        </thead>
        <tbody>
        {documentsOut.map((d: DocumentJson, i: number) =>
            <tr key={d.name}>
                <Document name={d.name} />
            </tr>)}
        </tbody>
    </table>;

    return <div>
        <h1>{t("documents.titleList")}</h1>
        {documentsTable}
        <h1>{t("documents.titleOutList")}</h1>
        {documentsOutTable}
    </div>
});
