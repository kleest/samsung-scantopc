import React from 'react';
import ReactDOM from 'react-dom/client';

import App from './App';
import "./styles.scss";


if (!new class { x: any }().hasOwnProperty('x')) throw new Error('Transpiler is not configured correctly');

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);
