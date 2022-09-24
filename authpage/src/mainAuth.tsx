import './index.css'
import React from 'react'
import {createRoot} from "react-dom/client";
import Auth from './Auth'
import ContainBack from "./ContainBack";

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <ContainBack component={<Auth />} />
</React.StrictMode>)

