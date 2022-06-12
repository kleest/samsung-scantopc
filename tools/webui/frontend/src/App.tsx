import {RootStoreProvider} from "store/RootStore";
import React, {useEffect} from "react";
import i18n from "i18n";
import {I18nextProvider, useTranslation} from "react-i18next";
import {observer} from "mobx-react-lite";
import {DocumentList} from "ui/DocumentList";
import {useUiStore} from "store/UiStore";

import "normalize.css";
import {IconEyeOff, IconRefresh} from "@tabler/icons";
import {PDFPreview} from "ui/PDFPreview";

type AppProps = {};

const AppContent: React.FC<AppProps> = observer(({}) => {
    const {t, i18n} = useTranslation();
    useEffect(() => {
        document.title = t('appName')
    }, [i18n.language]);

    const uiStore = useUiStore();

    useEffect(() => {
        uiStore.getDocuments();
        uiStore.getDocumentsOut();
    }, []);

    return (
        <>
            <div className="twoPane">
                <DocumentList />
                <div>
                    <span>
                        <button title={t("documents.buttonLoad")} onClick={(e) => {uiStore.getDocuments(); uiStore.getDocumentsOut()}}>
                            <IconRefresh />
                        </button>
                        {uiStore.previewUrl && <button title={t("documents.buttonPreviewClose")} onClick={(e) => uiStore.setPDFPreview("")}>
                            <IconEyeOff />
                        </button>}
                    </span>
                    <PDFPreview url={uiStore.previewUrl}/>
                </div>
            </div>
        </>
    );
});

export const App: React.FC<AppProps> = ({}) => {
    return (
        <I18nextProvider i18n={i18n}>
            <RootStoreProvider>
                <AppContent/>
            </RootStoreProvider>
        </I18nextProvider>
    );
};

export default App;
