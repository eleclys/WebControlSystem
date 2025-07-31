// src/App.js
// 建议：
// 1. 建立“确认机制”：设定目标值等参数后，用户可以点击“预测效果”，
//    页面上通过各种方式让用户知道这个操作会带来什么效果，然后用户可以选择是否确认该操作。
import React, {useState, useEffect} from 'react';
import {io} from 'socket.io-client';
import SetpointForm from './components/SetpointForm';
import PidForm from './components/PidForm';

function App() {
    const [setpoint, setSetpoint] = useState(70);
    const [currentTemp, setCurrentTemp] = useState(null);
    const [message, setMessage] = useState('');

    const [Kp, setKp] = useState(1.0);
    const [Ki, setKi] = useState(0.1);
    const [Kd, setKd] = useState(0.0);
    const [pidMessage, setPidMessage] = useState('');

    const [controllerStatus, setControllerStatus] = useState('');


    useEffect(() => {
        fetch('/api/temperature/setpoint')
            .then((res) => res.json())
            .then((data) => {
                if (data.setpoint !== null) {
                    setSetpoint(data.setpoint);
                }
            })
            .catch((err) => console.error("Get setpoint failed", err));

        fetch('/api/controller/params')
            .then(res => res.json())
            .then(data => {
                setKp(data.Kp);
                setKi(data.Ki);
                setKd(data.Kd);
            });

        fetch('/api/temperature/current')
            .then(res => res.json())
            .then(data => {
              if (data.current_temp !== null) setCurrentTemp(data.current_temp);
            })
            .catch(err => console.error("Get current data failed", err));

    }, []);

    useEffect(() => {
        const socket = io(window.location.origin);

        socket.on('setpoint_update', (data) => {
            setSetpoint(data.value);
            setMessage(`设定值通过 WebSocket 更新为：${data.value}`);
        });

        socket.on('current_temp_update', (data) => {
            setCurrentTemp(data.value);
        });

        socket.on('controller_params_update', (data) => {
            setKp(data.Kp);
            setKi(data.Ki);
            setKd(data.Kd);
            setPidMessage(`PID 参数已通过 WebSocket 更新`);
        });

        return () => socket.disconnect();
    }, []);

    return (
        <div style={{maxWidth: 500, margin: '2rem auto', fontFamily: 'Arial, sans-serif'}}>
            <h2>Temperature Control</h2>
            <p>Current temperature:{currentTemp !== null ? `${currentTemp}` : '获取中...'}</p>

            <SetpointForm
                setpoint={setpoint}
                setSetpoint={setSetpoint}
                message={message}
                setMessage={setMessage}
            />

            <hr style={{margin: '2rem 0'}}/>

            <PidForm
                Kp={Kp}
                Ki={Ki}
                Kd={Kd}
                setKp={setKp}
                setKi={setKi}
                setKd={setKd}
                pidMessage={pidMessage}
                setPidMessage={setPidMessage}
            />

            <div style={{marginTop: '2rem'}}>
                <button onClick={() => {
                    fetch('/api/controller/start', {method: 'POST'})
                        .then(res => res.json())
                        .then(data => setControllerStatus(data.message))
                        .catch(err => setControllerStatus('Start failed'));
                }}>Start
                </button>

                <button style={{marginLeft: '1rem'}} onClick={() => {
                    fetch('/api/controller/stop', {method: 'POST'})
                        .then(res => res.json())
                        .then(data => setControllerStatus(data.message))
                        .catch(err => setControllerStatus('Stop failed'));
                }}>Stop
                </button>

                {controllerStatus && <p style={{marginTop: '1rem'}}>{controllerStatus}</p>}
            </div>


        </div>
    );
}

export default App;
