import React, {useState} from "react";
import {observer} from "mobx-react-lite";
import {useTranslation} from "react-i18next";

import {
    Box,
    Button, ButtonGroup,
    Dialog,
    DialogActions,
    DialogContent,
    DialogContentText,
    DialogTitle,
    IconButton, InputAdornment, LinearProgress,
    List,
    ListItem,
    ListItemSecondaryAction,
    ListItemText, Menu, MenuItem, Select, Stack, styled, TextField
} from "@mui/material";

import Delete from "@mui/icons-material/Delete";
import AddCircleOutline from "@mui/icons-material/AddCircleOutline";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import ArrowDropUpIcon from "@mui/icons-material/ArrowDropUp";

import {useUiStore} from "store/UiStore";
import Typography from "@mui/material/Typography";

const ListItemTwoSecondaryActions = styled(ListItem)(({theme}) => ({
    "&.MuiListItem-secondaryAction": {
        paddingRight: 144
    }
}));

export type MergeDialogProps = {
    loading: boolean
    shown: boolean
    onCancel: () => void
    onConfirm: (selectedDocuments: string[], newName: string) => void
}
export const MergeDialog: React.FC<MergeDialogProps> = observer(({loading, shown, onCancel, onConfirm}) => {
    const {t} = useTranslation();
    const uiStore = useUiStore();

    const [addMenuAnchor, setAddMenuAnchor] = useState<null | HTMLElement>(null);
    const [mergedName, setMergedName] = useState("");

    // only display documents that are not already added
    const documentsToAdd = uiStore.documents.filter((d) => uiStore.mergeDocuments.indexOf(d.id) === -1);

    const addMergeDocument = (id: string) => {
        // close menu
        setAddMenuAnchor(null);
        // add document
        uiStore.addMergeDocument(id);
    }

    const documentsUi = uiStore.mergeDocumentsFull.map((document, i) =>
        <ListItemTwoSecondaryActions key={document.id}>
            <ListItemText>{document.name}</ListItemText>
            <ListItemSecondaryAction>
                <ButtonGroup>
                    <IconButton disabled={i === 0}
                                onClick={() => uiStore.moveMergeDocument(document.id, -1)}><ArrowDropUpIcon /></IconButton>
                    <IconButton disabled={i === uiStore.mergeDocumentsFull.length-1}
                                onClick={() => uiStore.moveMergeDocument(document.id, 1)}><ArrowDropDownIcon /></IconButton>
                    <IconButton onClick={() => uiStore.removeMergeDocument(document.id)}><Delete /></IconButton>
                </ButtonGroup>
            </ListItemSecondaryAction>
        </ListItemTwoSecondaryActions>
    );

    return <Dialog open={shown} onClose={onCancel}>
        {loading && <LinearProgress />}
        <DialogTitle>{t("dialog.merge.title")}</DialogTitle>
        <DialogContent>
            <DialogContentText>{t("dialog.merge.contentText")}</DialogContentText>
            <List dense={false}>
                {documentsUi.length > 0 ? documentsUi :
                    <ListItem key={-1}><ListItemText sx={{textAlign: "center"}}>
                        <Typography variant="body1"><i>{t("list.empty")}</i></Typography></ListItemText>
                    </ListItem>
                }
            </List>
            <Box sx={{textAlign: "right"}}>
                <Button variant="contained" startIcon={<AddCircleOutline />} disabled={documentsToAdd.length === 0}
                        onClick={(e) => setAddMenuAnchor(e.currentTarget)}>{t("dialog.merge.addDocument")}</Button>
            </Box>
            <Menu anchorEl={addMenuAnchor} open={!!addMenuAnchor} onClose={() => setAddMenuAnchor(null)}>
                {documentsToAdd.map((document) =>
                    <MenuItem key={document.id} onClick={() => addMergeDocument(document.id)}>{document.name}</MenuItem>)}
            </Menu>
            <TextField variant="standard" value={mergedName} fullWidth={true} required={true} error={mergedName === ""}
                       InputProps={{
                           endAdornment: <InputAdornment position="end">.pdf</InputAdornment>,
                       }}
                       onChange={(e) => setMergedName(e.target.value)} label={t("dialog.merge.mergedName")} />
        </DialogContent>
        <DialogActions>
            <Button disabled={loading} onClick={onCancel}>{t("action.cancel")}</Button>
            <Button disabled={loading || mergedName === "" || uiStore.mergeDocuments.length === 0} onClick={() => {
                setMergedName("");
                onConfirm(uiStore.mergeDocuments, mergedName + ".pdf");
            }}>{t("action.ok")}</Button>
        </DialogActions>
    </Dialog>;
});
