import React from "react";
import {useTranslation} from "react-i18next";

type Props = {
    url: string,
};

export const PDFPreview: React.FC<Props> = ({ url}) => {
    const {t} = useTranslation();
    return <div className="pdfPreview">{url && <iframe src={url}></iframe>}</div>;
};
