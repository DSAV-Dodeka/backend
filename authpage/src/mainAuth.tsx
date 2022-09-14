import './index.css'
import React from 'react'
import {createRoot} from "react-dom/client";
import Auth from './Auth'

const container = document.getElementById('root')
const root = createRoot(container!)
root.render(<React.StrictMode>
    <Auth />
</React.StrictMode>)

