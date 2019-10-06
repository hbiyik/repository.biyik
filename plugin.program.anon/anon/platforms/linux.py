'''
Created on Sep 30, 2019

@author: z0042jww
'''
import re
import os
import gzip
import subprocess


from . import Base
from . import defs


class Platform(Base):
    def init(self, machineid, getinput):
        self.machineid = machineid
        self.getinput = getinput
        self.cfg["network_interface"] = "auto"
        self.cfg["iptables_fwmark"] = "0x6"
        self.cfg["routing_policy_table_number"] = "600"
        self.sudopw = None

    def missing_reqs(self):
        # check kernel
        self.torrc = os.path.join(self.tempdir, "torrc")
        self.ovpncfg = os.path.join(self.tempdir, "ovpncfg")
        self.ovpncred = os.path.join(self.tempdir, "ovpncred")
        haswarning = False

        msg = ""
        for msg in self.check_kernel():
            msg += msg + "\n"
            haswarning = True
        if len(msg):
            yield "%s\n above requirements are not satisfied by your kernel" % msg

        # check userspace tools
        tools = (("IP tool not found.\nThis addon needs ip tool to be installed in your system.\nPlease use your package manager to install it", "ip -V"),
                 ("IPTables ot found.\nThis addon needs iptables to be installed in your system.\nPlease use your package manager or to install it", "iptables -V"),
                 ("OPENVPN.\nThis addon needs OPENVPN to be installed in your system.\nPlease use your package manager or to install it", "openvpn --help"),
                 ("TOR.\nThis addon needs TOR to be installed in your system.\nPlease use your package manager or to install it", "tor --help"),
                 )

        hasiptables = True
        for warning, command in tools:
            process = self.run_cmd(command, False)
            if not process:
                if "iptables" in command:
                    hasiptables = False
                haswarning = True
                yield warning
#            else:
#                process.wait()
#                if process.returncode:
#                    yield "%s tool not found" % tool
        if hasiptables and not haswarning:
            itables = self.run_cmd("iptables -L", False)
            itables.wait()
            if itables.returncode:
                pw = self.getinput("Root Password required")
                echo = subprocess.Popen(['echo', pw], stdout=subprocess.PIPE)
                sudo = subprocess.Popen(['sudo', '-S', 'iptables', '-w', '-L'], stdin=echo.stdout,
                                        stdout=subprocess.PIPE)
                sudo.wait()
                if sudo.returncode:
                    yield "Can't get root privilieges"
                else:
                    self.sudopw = pw

        for key in self.cfg.keys():
            val = self.getsetting(key)
            if key == "tor_limit_nodes_to" and not len(val):
                yield "You need to enable at least one region for tor nodes"
            if key == "tor_limit_exit_nodes_to" and not len(val):
                yield "You need to enable at least one region for tor exit nodes"
            if val == "?":
                yield "'%s' configuration value is not valid" % key.replace("_", " ").title()

    def check_kernel(self):
        req_kernel_keys = ["CONFIG_IP_NF_TARGET_REJECT",
                           "CONFIG_NF_NAT_IPV4",
                           "CONFIG_IP_NF_MANGLE",
                           "CONFIG_NETFILTER_XT_TARGET_REDIRECT",
                           "CONFIG_NETFILTER_XT_MARK",
                           "CONFIG_NETFILTER_XT_MATCH_U32",
                           "CONFIG_NETFILTER_XT_MATCH_OWNER"]

        def check_kernel_config(output):
            for kernel_key in req_kernel_keys:
                search = re.search(kernel_key + "\=(.)", output, re.IGNORECASE)
                if not search or search.group(1).lower() not in ["m", "y"]:
                    yield kernel_key

        def safeopen(path, gz=False):
            if os.path.exists(path):
                try:
                    if gz:
                        f = gzip.open(path)
                    else:
                        f = open(path)
                    return f.read()
                except Exception:
                    pass

        # configs kernel module test
        modprobe = self.run_cmd("modprobe configs", False)
        modprobe.wait()
        if not modprobe.returncode:
            zcat = safeopen("/proc/config.gz", True)
            if zcat:
                for msg in check_kernel_config(zcat):
                    yield msg
                raise StopIteration
        else:
            # debian way of kernel config
            uname = list(self.run_cmd("uname -r"))
            if len(uname):
                config = safeopen("/boot/config-%s" % uname[0][:-1])
                if config:
                    for msg in check_kernel_config(config):
                        yield msg
                    raise StopIteration
        yield "Unknown kernel configuration"

    def run_cmd(self, command, stdout=True):
        print command
        stdin = None
        if self.sudopw:
            echo = subprocess.Popen(['echo', self.sudopw], stdout=subprocess.PIPE)
            command = "sudo -S %s" % command
            stdin = echo.stdout
        return Base.run_cmd(self, command, stdout, stdin)

    def run_sec(self, command, panic=True):
        popen = self.run_cmd(command, False)
        popen.wait()
        if popen.returncode:
            if panic:
                raise Exception("%s error code on running %s" % (popen.returncode, command))
                return False
            else:
                return False
        else:
            return True

    def default_if_gw(self):
        for line in self.run_cmd("ip route show"):
            defroute = re.search("default via ([0-9\.]+) dev (.+?)\s", line)
            if defroute:
                return defroute.group(1), defroute.group(2)
        return "?", "?"

    def if_ip_subnet(self, dev):
        # TODO: IMPROVE: what happens if interface has multiple ips, which interface to route
        # tor from for direct connection?
        for line in self.run_cmd("ip addr show %s" % dev):
            subnet = re.search("inet\s([0-9\.\/]+)", line)
            if subnet:
                ip = subnet.group(1).split("/")
                if len(ip) == 2:
                    return ip[0], subnet.group(1)

    def reset(self):
        list(self.run_cmd("iptables -w -F"))
        list(self.run_cmd("iptables -w -t nat -F"))
        list(self.run_cmd("iptables -w -t mangle -F"))
        list(self.run_cmd("ip route flush table %s" % self.cfg["routing_policy_table_number"]))
        list(self.run_cmd("ip rule del fwmark %s table %s" % (self.cfg["iptables_fwmark"],
                                                              self.cfg["routing_policy_table_number"])))
        return True

    def start_ovpn(self):
        self.tunnel_type = self.tunnel_remote_address = self.tunnel_remote_port = None
        self.tunnel_device = self.tunnel_local = self.tunnel_peer = tunnel_route_gw = None
        self.tunnel_route = []
        # dump settings to temp files
        with open(self.ovpncfg, "w") as f:
            f.write(self.cfg["openvpn_config"])
        with open(self.ovpncred, "w") as f:
            f.write("%s\n%s" % (self.cfg["openvpn_username"], self.cfg["openvpn_password"]))
        lines = self.run_cmd('openvpn --config %s --auth-user-pass %s --route-noexec' % (self.ovpncfg,
                                                                                         self.ovpncred))
        for line in lines:
            remote = re.search("link\sremote.+?\[(.+)\]([0-9\.]+)\:([0-9]+)", line)
            # TODO: IMPROVE: It is possible to have ovpn tunnel to push multiple tunnels?
            self.tunnel_route.extend(re.findall("PUSH\:\sReceived\scontrol\smessage\:.+route\s([0-9|.]+)", line))
            if not tunnel_route_gw:
                tunnel_route_gw = re.search("PUSH\:\sReceived\scontrol\smessage\:.+route\-gateway\s([0-9|.]+)", line)
            device = re.search("ip\saddr\sadd\sdev\s(.+)\slocal\s([0-9\.]+)\speer\s([0-9\.]+)", line)
            device2 = re.search("ip\saddr\sadd\sdev\s(.+)\s([0-9\.]+)\/", line)
            if remote:
                self.tunnel_type = remote.group(1)
                self.tunnel_remote_address = remote.group(2)
                self.tunnel_remote_port = remote.group(3)
            if device:
                self.tunnel_device = device.group(1)
                self.tunnel_local = device.group(2)
                self.tunnel_peer = device.group(3)
            elif device2 and tunnel_route_gw:
                self.tunnel_device = device2.group(1)
                self.tunnel_local = device2.group(2)
                self.tunnel_peer = tunnel_route_gw.group(1)
            if self.tunnel_type and self.tunnel_remote_address and \
                self.tunnel_remote_port and self.tunnel_local and self.tunnel_peer and self.tunnel_device:
                return True
                # TODO: IMPROVE: implement timeout in case openvpn does not start up for some reason

    def start_tor(self, cmdline=None):
        with open(self.torrc, "w") as f:
            f.write("VirtualAddrNetwork 10.192.0.0/10\n")
            f.write("AutomapHostsOnResolve 1\n")
            f.write("StrictNodes 0\n")
            f.write("TransPort 127.0.0.1:%s\n" % self.cfg["tor_tcp_port"])
            f.write("DNSPort 127.0.0.1:%s\n" % self.cfg["tor_dns_port"])
            f.write("ControlPort 127.0.0.1:%s\n" % self.cfg["tor_control_port"])
            f.write("ExcludeNodes ")
            limit_nodes_index = self.getsetting("tor_limit_nodes_to")
            for i, country in enumerate(defs.tor_countries):
                if i not in limit_nodes_index:
                    f.write("{%s}," % country)
            f.write("\nExitNodes ")
            limit_nodes_index = self.getsetting("tor_limit_exit_nodes_to")
            for i, country in enumerate(defs.tor_countries):
                if i in limit_nodes_index:
                    f.write("{%s}," % country)
            f.write("\n")
        if not cmdline:
            cmdline = "tor -f %s" % self.torrc
        lines = self.run_cmd(cmdline)
        # os.remove(self.torrc)
        for line in lines:
            if re.search("Bootstrapped\s100\%\:\sDone", line):
                return True
        # TODO: IMPROVE: implement timeout in case tor does not start up for some reason

    def anonymize(self):
        for cmd in ["id -u debian-tor", "id -u tor", "docker exec -u debian-tor tor id -u"]:
            tor_uid = list(self.run_cmd(cmd))
            if len(tor_uid):
                break
        if not len(tor_uid):
            raise Exception("Can't find TOR UID")

        list(self.run_cmd("sysctl net.ipv4.conf.all.src_valid_mark=1"))

        # block utp protcol
        self.run_sec('iptables -w -A OUTPUT -m udp -p udp -m u32 --u32 "26&0xFFFF=0x100" -j REJECT') # utp-data
        self.run_sec('iptables -w -A OUTPUT -m udp -p udp -m u32 --u32 "26&0xFFFF=0x1100" -j REJECT') # utp-fin
        self.run_sec('iptables -w -A OUTPUT -m udp -p udp -m u32 --u32 "26&0xFFFF=0x2100" -j REJECT') # utp-state
        self.run_sec('iptables -w -A OUTPUT -m udp -p udp -m u32 --u32 "26&0xFFFF=0x3100" -j REJECT') # utp-reset
        self.run_sec('iptables -w -A OUTPUT -m udp -p udp -m u32 --u32 "26&0xFFFF=0x4100" -j REJECT') # utp-syn

        # nat table
        # Allow TOR instance direct communication
        rulenum = 1
        # TODO: IMPROVE: allow openvpn also to pass thorugh tor tcp forwarding
        self.run_sec("iptables -w -t nat -I OUTPUT %s -m owner --uid-owner %s -j RETURN" % (rulenum,
                                                                                            tor_uid[0]))
        rulenum += 1
        # redirect dns requests to tor dns port
        self.run_sec("iptables -w -t nat -I OUTPUT %s -d 127.0.0.1/32 -p udp -m udp --dport 53 -j REDIRECT --to-ports %s" % (rulenum,
                                                                                                                             self.cfg["tor_dns_port"]))

        # return all IANA specified local adresses from nat table 
        for nontor in self.nontors:
            rulenum += 1
            self.run_sec("iptables -w -t nat -I OUTPUT %s -d %s -j RETURN" % (rulenum, nontor))

        # redirect all left tcp requests to tor
        rulenum += 1
        self.run_sec("iptables -w -t nat -I OUTPUT %s -p tcp --syn -j REDIRECT --to-ports %s" %
                     (rulenum, self.cfg["tor_tcp_port"]))
        # fix source address of the policy routed udp packets
        self.run_sec("iptables -w -t nat -A POSTROUTING -p udp -o %s -j SNAT --to-source=%s" %
                     (self.tunnel_device, self.tunnel_local))

        # mangle table
        # return all IANA specified local adresses from mangle table
        rulenum = 0
        for nontor in self.nontors:
            rulenum += 1
            self.run_sec("iptables -w -t mangle -I OUTPUT %s -d %s -j RETURN" % (rulenum, nontor))
        # mark rest of the udp packets
        rulenum += 1
        self.run_sec("iptables -w -t mangle -I OUTPUT %s -m udp -p udp -j MARK --set-mark %s" %
                     (rulenum, self.cfg["iptables_fwmark"]))

        # policy route the marked packets to VPN
        self.run_sec("ip rule add fwmark %s table %s" % (self.cfg["iptables_fwmark"],
                                                         self.cfg["routing_policy_table_number"]))

        self.run_sec("ip route add %s/32 via %s table %s" %
                     (self.tunnel_remote_address, self.defaultgw,
                      self.cfg["routing_policy_table_number"]))
        self.run_sec("ip route add 0.0.0.0/1 via %s table %s" %
                     (self.tunnel_peer, self.cfg["routing_policy_table_number"]))
        self.run_sec("ip route add 128.0.0.0/1 via %s table %s" %
                     (self.tunnel_peer, self.cfg["routing_policy_table_number"]))
        for route in self.tunnel_route:
            if "/" not in route:
                route = "%s/32" % route
            self.run_sec("ip route add %s via %s table %s" %
                         (route, self.tunnel_peer, self.cfg["routing_policy_table_number"]))
        return True

    def stop_tor(self):
        list(self.run_cmd("killall tor"))
        return True

    def stop_ovpn(self):
        list(self.run_cmd("killall openvpn"))
        """
        while True:
            stop = True
            for _ in self.findpids("openvpn"):
                stop = False
            if stop:
                break
        """
        return True

    def set_dns(self, *dnss):
        if self.sudopw:
            return True
        else:
            with open("/etc/resolv.conf", "w") as f:
                for dns in dnss:
                    f.write("nameserver %s\n" % dns)
                    return True

    def findpids(self, process):
        for line in self.run_cmd("ps -A"):
            search = re.search("([0-9]+)\s.*?(.)" + process + "(.?)", line)
            if search and not search.group(2) == "[" and not search.group(3) == "]":
                yield int(search.group(1))

    def stats(self):
        stats = {}
        for line in self.run_cmd("iptables -w -L -v -n -t nat"):
            dns = re.search("([0-9\K\G\M\T]+)\s.*?udp\sdpt\:53\sredir\sports\s" +
                            self.getsetting("tor_dns_port"), line)
            tcp = re.search("([0-9\K\G\M\T]+)\s.*?tcp\sflags\:0x17\/0x02\sredir\sports\s" +
                            self.getsetting("tor_tcp_port"), line)
            udp = re.search("([0-9\K\G\M\T]+)\s.*?udp.*?to\:[0-9\.]+", line)
            if dns:
                stats["dns_packets_routed_to_tor"] = dns.group(1)
            if tcp:
                stats["tcp_packets_routed_to_tor"] = tcp.group(1)
            if udp:
                stats["udp_packets_routed_to_vpn"] = udp.group(1)
        """
        for line in self.run_cmd("iptables -w -L -v -n -t mangle"):
            udp = re.search("([0-9\K\G\M\T]+)\s.*?udp\sMARK\sset\s" +
                             self.getsetting("iptables_fwmark"), line)
            if udp:
                stats["udp_packets_routed_to_vpn"] = udp.group(1)
        """
        utppackets = []
        for line in self.run_cmd("iptables -w -L -v -n"):
            for mark in ["0x100", "0x1100", "0x2100", "0x3100", "0x4100"]:
                utp = re.search("([0-9\K\G\M\T]+)\s.*?udp\su32\s\"0x1a\&0xffff\=" +
                                mark + "\"\sreject\-with\sicmp\-port\-unreachable", line)
                if utp:
                    utppackets.append(utp.group(1))
        if len(utppackets):
            stats["blocked_utp_packets"] = ", ".join(utppackets)
        return stats
