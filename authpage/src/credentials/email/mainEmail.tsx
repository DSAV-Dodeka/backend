import '../../index.scss'
import React from 'react'
import {createRoot} from "react-dom/client";
import Email from "./Email";

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <Email />
</React.StrictMode>)