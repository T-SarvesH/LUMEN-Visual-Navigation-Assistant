#!/bin/bash
# Get the first IP address from hostname -I
hostname -I | awk '{print $1}'
