import React from "react";

type Props = {
    url: string,
};

export const PDFPreview: React.FC<Props> = ({ url}) => {
    return <>{url && <iframe src={url} style={{border: "0"}}></iframe>}</>;
};
