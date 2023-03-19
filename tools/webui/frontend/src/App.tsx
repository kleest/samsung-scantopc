import {RootStoreProvider} from "store/RootStore";
import React, {useEffect, useState} from "react";
import i18n from "i18n";
import {I18nextProvider, useTranslation} from "react-i18next";
import {observer} from "mobx-react-lite";
import {
    Box, CircularProgress,
    Container,
    createTheme,
    CssBaseline, IconButton,
    Paper, Stack, ThemeProvider,
    useMediaQuery
} from "@mui/material";
import Grid from '@mui/material/Unstable_Grid2';

import {DocumentList, DocumentListOut} from "ui/DocumentList";
import {useUiStore} from "store/UiStore";

import RefreshIcon from "@mui/icons-material/Refresh";
import CloseIcon from "@mui/icons-material/Close";
import MergeIcon from "@mui/icons-material/Merge";

import {PDFPreview} from "ui/PDFPreview";

// fonts
import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import {GrowingSpace} from "ui/ReusableComponents";
import {MergeDialog} from "ui/MergeDialog";


type CardProps = {
    children?: React.ReactNode;
    sx?: object
}
const Card: React.FC<CardProps> = ({children, sx = {}}) => {
    return <Paper sx={{
        p: 2,
        ...sx
    }} elevation={3}>{children}</Paper>;
};

const AppContent: React.FC = observer(({}) => {
    const {t, i18n} = useTranslation();
    useEffect(() => {
        document.title = t('appName')
    }, [i18n.language]);

    const uiStore = useUiStore();

    useEffect(() => {
        uiStore.getDocuments();
        uiStore.getDocumentsOut();
    }, []);

    const [spin, setSpin] = useState(false);
    const [mergeDialogShown, setMergeDialogShow] = useState(false);
    const [mergeDialogLoading, setMergeDialogLoading] = useState(false);

    const hasPreview = !!uiStore.previewUrl;

    return (
        <Box sx={{display: "flex"}}>
            <Box
                component={"main"} sx={{
                flexGrow: 1, height: "100vh"
            }}>
                <Container maxWidth={false} sx={{pt: 2, pb: 2, height: "100vh"}}>
                    <Stack direction="column" height={"100%"}>
                        {/* controls */}
                        <Stack direction="row" sx={{
                            mb: 1
                        }}>
                            <IconButton title={t("documents.buttonLoad")} onClick={(e) => {
                                setSpin(true);
                                Promise.allSettled([uiStore.getDocuments(), uiStore.getDocumentsOut()])
                                    .then(() => setSpin(false));
                            }}>
                                {spin ? <CircularProgress size={24}/> : <RefreshIcon/>}
                            </IconButton>
                            {/* merge action */}
                            <IconButton title={t("documents.buttonMerge")} onClick={() => setMergeDialogShow(true)}>
                                <MergeIcon />
                            </IconButton>
                            <MergeDialog loading={mergeDialogLoading} shown={mergeDialogShown} onCancel={() => setMergeDialogShow(false)}
                                         onConfirm={(selectedDocuments, newName) => {
                                             setMergeDialogLoading(true);
                                             uiStore.doMergeDocuments(selectedDocuments, newName).then(() => {
                                                 setMergeDialogLoading(false);
                                                 setMergeDialogShow(false);
                                             });
                                         }} />
                            {/* -- */}
                            <GrowingSpace/>
                            {uiStore.previewUrl && <IconButton title={t("documents.buttonPreviewClose")} onClick={(e) => uiStore.setPDFPreview("")}>
                                <CloseIcon/>
                            </IconButton>}
                        </Stack>
                        {/* document lists + PDF preview */}
                        <Grid container spacing={2}>
                            <Grid xs={12} lg={7} xl={hasPreview ? 5 : 7}>
                                <Card><DocumentList/></Card>
                            </Grid>
                            <Grid xs={12} lg={5} xl={hasPreview ? 3 : 5}>
                                <Card><DocumentListOut/></Card>
                            </Grid>
                            {hasPreview && <Grid xs={12} xl={4} height={"90vh"}>
                                <Card sx={{
                                    p: 0,
                                    height: "100%",
                                    width: "100%",
                                    "> iframe": {
                                        display: "block",
                                        boxSizing: "border-box",
                                        width: "100%",
                                        height: "100%",
                                    }
                                }}><PDFPreview url={uiStore.previewUrl}/></Card>
                            </Grid>}
                        </Grid>
                    </Stack>
                </Container>
            </Box>
        </Box>
    );
});

export const App: React.FC = () => {
    const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');
    const theme = React.useMemo(() => createTheme({
            palette: {
                mode: prefersDarkMode ? 'dark' : 'light',
            },
        }), [prefersDarkMode],
    );

    return (
        <I18nextProvider i18n={i18n}>
            <RootStoreProvider>
                <ThemeProvider theme={theme}>
                    <CssBaseline/>
                    <AppContent/>
                </ThemeProvider>
            </RootStoreProvider>
        </I18nextProvider>
    );
};

export default App;
