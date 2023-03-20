import {Button, Dialog, DialogActions, DialogContent, DialogContentText, DialogTitle, Stack, StackProps, styled} from "@mui/material";
import React from "react";
import {useTranslation} from "react-i18next";

export const FlexStack = styled(Stack)<StackProps>({display: "flex", "& > *": {flex: "1"}});
export const GrowingSpace = styled("div")({
    flex: "1 1 auto"
});

export type ConfirmationDialogProps = {
    titleText: string
    contentText: string
    open: boolean
    onConfirm: () => void
    onCancel: () => void
}
export const ConfirmationDialog: React.FC<ConfirmationDialogProps> = ({titleText, contentText, open, onConfirm, onCancel}) => {
    const {t} = useTranslation();

    return <Dialog
        open={open}
    >
        <DialogTitle>
            {titleText}
        </DialogTitle>
        <DialogContent>
            <DialogContentText>
                {contentText}
            </DialogContentText>
        </DialogContent>
        <DialogActions>
            <Button onClick={onCancel}>{t("action.cancel")}</Button>
            <Button onClick={onConfirm}>{t("action.ok")}</Button>
        </DialogActions>
    </Dialog>;
}
